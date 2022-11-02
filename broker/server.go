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
	return &BrokerServer{
		broker: NewBroker(),
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

func (s *BrokerServer) GetWork(ctx context.Context, in *pb.WorkerMessage) (*pb.NodeMessage, error) {
	log.Printf("Get work")
	worker := s.broker.GetWorker(in.Identifier)
	node := s.broker.PopNextNode(worker)

	if node == nil {
		return nil, errors.New("no work available")
	}

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) SubmitWork(ctx context.Context, in *pb.WorkCompleteMessage) (*pb.NodeMessage, error) {
	log.Printf("Submit work")
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
			FunctionName:  source.functionName,
			Arguments:     source.arguments,
			ResolvedValue: source.resolvedValue,
			Completed:     source.completed,
		}
		sourceMessages = append(sourceMessages, message)
	}

	return &pb.NodeMessage{
		Identifier:    node.identifier,
		FunctionName:  node.functionName,
		Arguments:     node.arguments,
		ResolvedValue: node.resolvedValue,
		Sources:       sourceMessages,
		Completed:     node.completed,
		InstanceId:    node.instance.identifier,
	}
}
