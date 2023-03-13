package main

import (
	pb "dagorama/api"
	"fmt"
	"log"
	"net"

	"google.golang.org/grpc"
)

func main() {
	config := loadConfig()

	serveAddress := fmt.Sprintf("%s:%d", config.host, config.port)

	conn, err := net.Listen("tcp", serveAddress)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	log.Printf("Broker service will start on `%s`...", serveAddress)
	pb.RegisterDagoramaServer(grpcServer, NewBrokerServer())
	grpcServer.Serve(conn)
}
