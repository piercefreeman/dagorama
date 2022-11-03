package main

import (
	"context"
	pb "dagorama/api"
	"errors"
	"log"
)

type BrokerServer struct {
	pb.UnimplementedDagoramaServer

	broker *Broker
}

func NewBrokerServer() *BrokerServer {
	broker := NewBroker()

	// GC should run in the background periodically. The function will own
	// its own wakeup logic and will run forever.
	go broker.GarbageCollectWorkers()

	return &BrokerServer{
		broker: broker,
	}
}

func (s *BrokerServer) CreateWorker(ctx context.Context, in *pb.WorkerConfigurationMessage) (*pb.WorkerMessage, error) {
	log.Printf("Creating worker")
	worker := s.broker.NewWorker(in.ExcludeQueues, in.IncludeQueues, in.QueueTolerations)
	return &pb.WorkerMessage{Identifier: worker.identifier}, nil
}

func (s *BrokerServer) CreateInstance(ctx context.Context, in *pb.InstanceConfigurationMessage) (*pb.InstanceMessage, error) {
	log.Printf("Creating instance")
	instance := s.broker.NewInstance(in.Identifier)
	return &pb.InstanceMessage{Identifier: instance.identifier}, nil
}

func (s *BrokerServer) CreateNode(ctx context.Context, in *pb.NodeConfigurationMessage) (*pb.NodeMessage, error) {
	log.Printf("Creating node")
	instance := s.broker.GetInstance(in.InstanceId)

	// Map sources to nodes
	sourceNodes := make([]*DAGNode, 0)
	for _, source := range in.SourceIds {
		sourceNodes = append(sourceNodes, instance.GetNode(source))
	}

	node := instance.NewNode(
		in.Identifier,
		in.FunctionName,
		in.FunctionHash,
		in.QueueName,
		in.TaintName,
		in.Arguments,
		sourceNodes,
	)
	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) Ping(ctx context.Context, in *pb.WorkerMessage) (*pb.PongMessage, error) {
	log.Printf("Ping worker")
	worker := s.broker.GetWorker(in.Identifier)
	worker.Ping()

	return &pb.PongMessage{
		LastPing: worker.lastPing,
	}, nil
}

func (s *BrokerServer) GetNode(ctx context.Context, in *pb.NodeRetrieveMessage) (*pb.NodeMessage, error) {
	log.Printf("Get node")
	instance := s.broker.GetInstance(in.InstanceId)
	node := instance.GetNode(in.Identifier)

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) GetWork(ctx context.Context, in *pb.WorkerMessage) (*pb.NodeMessage, error) {
	log.Printf("Get work")
	worker := s.broker.GetWorker(in.Identifier)

	if worker.invalidated {
		return nil, errors.New("worker invalidated")
	}

	node := s.broker.PopNextNode(worker)

	if node == nil {
		return nil, errors.New("no work available")
	}

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) SubmitWork(ctx context.Context, in *pb.WorkCompleteMessage) (*pb.NodeMessage, error) {
	log.Printf("Submit work")
	worker := s.broker.GetWorker(in.WorkerId)

	if worker.invalidated {
		return nil, errors.New("worker invalidated")
	}

	instance := s.broker.GetInstance(in.InstanceId)
	node := instance.GetNode(in.NodeId)
	node.ValueDidResolve(in.Result)

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) nodeToMessage(node *DAGNode) *pb.NodeMessage {
	// Convert the layer of sources to messages of their own
	// Only include one layer further of source messages
	sourceMessages := make([]*pb.NodeMessage, 0)

	for _, source := range node.sources {
		// We don't include the source of these messages
		message := &pb.NodeMessage{
			Identifier:    source.identifier,
			ResolvedValue: source.resolvedValue,
			Completed:     source.completed,
		}
		sourceMessages = append(sourceMessages, message)
	}

	return &pb.NodeMessage{
		Identifier:    node.identifier,
		FunctionName:  node.functionName,
		FunctionHash:  node.functionHash,
		QueueName:     node.queueName,
		TaintName:     node.taintName,
		Arguments:     node.arguments,
		ResolvedValue: node.resolvedValue,
		Sources:       sourceMessages,
		Completed:     node.completed,
		InstanceId:    node.instance.identifier,
	}
}
