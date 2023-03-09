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

	serveAddress := fmt.Sprintf("%s:%d", *host, *port)

	flag.Parse()
	conn, err := net.Listen("tcp", serveAddress)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	log.Printf("Broker service will start on `%s`...", serveAddress)
	pb.RegisterDagoramaServer(grpcServer, NewBrokerServer())
	grpcServer.Serve(conn)
}
