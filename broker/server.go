package main

import (
	"context"
	pb "dagorama/api"
	"errors"
)

type BrokerServer struct {
	pb.UnimplementedDagoramaServer

	broker *Broker
}

func NewBrokerServer() *BrokerServer {
	return &BrokerServer{}
}

func (s *BrokerServer) CreateWorker(ctx context.Context, in *pb.WorkerConfigurationMessage) (*pb.WorkerMessage, error) {
	worker := s.broker.NewWorker(in.ExcludeQueues, in.IncludeQueues, in.QueueTolerations)
	return &pb.WorkerMessage{Identifier: worker.identifier}, nil
}

func (s *BrokerServer) CreateInstance(ctx context.Context, in *pb.InstanceConfigurationMessage) (*pb.InstanceMessage, error) {
	instance := s.broker.NewInstance(in.Identifier)
	return &pb.InstanceMessage{Identifier: instance.identifier}, nil
}

func (s *BrokerServer) CreateNode(ctx context.Context, in *pb.NodeConfigurationMessage) (*pb.DAGNodeMessage, error) {
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
	worker := s.broker.GetWorker(in.Identifier)
	worker.Ping()

	return &pb.PongMessage{
		LastPing: worker.lastPing,
	}, nil
}

func (s *BrokerServer) GetWork(ctx context.Context, in *pb.WorkerMessage) (*pb.DAGNodeMessage, error) {
	worker := s.broker.GetWorker(in.Identifier)
	node := s.broker.PopNextNode(worker)

	if node == nil {
		return nil, errors.New("no work available")
	}

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) nodeToMessage(node *DAGNode) *pb.DAGNodeMessage {
	// Convert the layer of sources to messages of their own
	// Only include one layer further of source messages
	sourceMessages := make([]*pb.DAGNodeMessage, 0)

	for _, source := range node.sources {
		// We don't include the source of these messages
		message := &pb.DAGNodeMessage{
			Identifier:    source.identifier,
			FunctionName:  source.functionName,
			Arguments:     source.arguments,
			ResolvedValue: source.resolvedValue,
			Completed:     source.completed,
		}
		sourceMessages = append(sourceMessages, message)
	}

	return &pb.DAGNodeMessage{
		Identifier:    node.identifier,
		FunctionName:  node.functionName,
		Arguments:     node.arguments,
		ResolvedValue: node.resolvedValue,
		Sources:       sourceMessages,
		Completed:     node.completed,
	}
}
