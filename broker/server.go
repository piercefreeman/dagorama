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
	config := loadConfig()
	broker := NewBroker(config)

	// GC should run in the background periodically. The function will own
	// its own wakeup logic and will run forever.
	go broker.GarbageCollectWorkers()
	go broker.QueueFutureScheduled()

	return &BrokerServer{
		broker: broker,
	}
}

func (s *BrokerServer) CreateWorker(ctx context.Context, in *pb.WorkerConfigurationMessage) (*pb.WorkerMessage, error) {
	s.broker.logger.Debug("Creating worker")
	worker := s.broker.NewWorker(in.ExcludeQueues, in.IncludeQueues, in.QueueTolerations)
	return &pb.WorkerMessage{Identifier: worker.identifier}, nil
}

func (s *BrokerServer) CreateInstance(ctx context.Context, in *pb.InstanceConfigurationMessage) (*pb.InstanceMessage, error) {
	s.broker.logger.Debug("Creating instance")
	instance := s.broker.NewInstance(in.Identifier)
	return &pb.InstanceMessage{Identifier: instance.identifier}, nil
}

func (s *BrokerServer) CreateNode(ctx context.Context, in *pb.NodeConfigurationMessage) (*pb.NodeMessage, error) {
	s.broker.logger.Debug("Creating node")
	instance := s.broker.GetInstance(in.InstanceId)

	// Map sources to nodes
	sourceNodes := make([]*DAGNode, 0)
	for _, source := range in.SourceIds {
		sourceNodes = append(sourceNodes, instance.GetNode(source))
	}

	var retryPolicy *RetryPolicy
	if in.Retry != nil {
		if in.Retry.StaticInterval > 0 {
			retryPolicy = NewStaticRetryPolicy(int(in.Retry.StaticInterval), int(in.Retry.MaxAttempts))
		} else if in.Retry.ExponentialBase > 0 {
			retryPolicy = NewExponentialRetryPolicy(int(in.Retry.ExponentialBase), int(in.Retry.MaxAttempts))
		}
	}

	node := instance.NewNode(
		in.Identifier,
		in.FunctionName,
		in.FunctionHash,
		in.QueueName,
		in.TaintName,
		in.Arguments,
		sourceNodes,
		retryPolicy,
	)
	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) Ping(ctx context.Context, in *pb.WorkerMessage) (*pb.PongMessage, error) {
	s.broker.logger.Debug("Ping submitted from worker")
	worker := s.broker.GetWorker(in.Identifier)
	worker.Ping()

	return &pb.PongMessage{
		LastPing: worker.lastPing,
	}, nil
}

func (s *BrokerServer) GetNode(ctx context.Context, in *pb.NodeRetrieveMessage) (*pb.NodeMessage, error) {
	s.broker.logger.Debug("Get node")
	instance := s.broker.GetInstance(in.InstanceId)
	node := instance.GetNode(in.Identifier)

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) GetWork(ctx context.Context, in *pb.WorkerMessage) (*pb.NodeMessage, error) {
	s.broker.logger.Debug("Get work")
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
	s.broker.logger.Debug("Submit work")
	worker := s.broker.GetWorker(in.WorkerId)

	if worker.invalidated {
		return nil, errors.New("worker invalidated")
	}

	instance := s.broker.GetInstance(in.InstanceId)
	node := instance.GetNode(in.NodeId)
	node.ExecutionDidResolve(in.Result)

	return s.nodeToMessage(node), nil
}

func (s *BrokerServer) SubmitFailure(ctx context.Context, in *pb.WorkFailedMessage) (*pb.NodeMessage, error) {
	s.broker.logger.Debug("Submit failure")
	worker := s.broker.GetWorker(in.WorkerId)

	if worker.invalidated {
		return nil, errors.New("worker invalidated")
	}

	instance := s.broker.GetInstance(in.InstanceId)
	node := instance.GetNode(in.NodeId)
	node.ExecutionDidFail(in.Traceback)

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
