FROM golang:alpine AS builder

COPY broker /broker

RUN cd /broker && go mod download
RUN cd /broker && go build .

FROM alpine:3 AS broker

COPY --from=builder /broker/dagorama /broker

ENTRYPOINT ["/broker"]
