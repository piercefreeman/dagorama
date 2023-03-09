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
		host = flag.String("host", "localhost", "The host to mount the broker")
		port = flag.Int("port", 50051, "The port to listen on")
	)

	flag.Parse()
	conn, err := net.Listen("tcp", fmt.Sprintf("%s:%d", *host, *port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	log.Printf("Broker service will start on `localhost:%d`...", *port)
	pb.RegisterDagoramaServer(grpcServer, NewBrokerServer())
	grpcServer.Serve(conn)
}
