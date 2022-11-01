package main

import (
	pb "dagorama/api"
	"flag"
	"fmt"
	"log"
	"net"

	"google.golang.org/grpc"
)

func main() {
	var (
		port = flag.Int("port", 6021, "The port to listen on")
	)

	flag.Parse()
	conn, err := net.Listen("tcp", fmt.Sprintf("localhost:%d", *port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	log.Printf("Broker service will start...")
	pb.RegisterDagoramaServer(grpcServer, NewBrokerServer())
	grpcServer.Serve(conn)
}
