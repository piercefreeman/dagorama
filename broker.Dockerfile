FROM golang:alpine AS builder

COPY broker/go.mod /broker/go.mod
COPY broker/go.sum /broker/go.sum
RUN cd /broker && go mod download

COPY broker /broker
RUN cd /broker && go build .

FROM alpine:3 AS broker

ENV HOST=0.0.0.0
ENV PORT=50051

COPY --from=builder /broker/dagorama /broker
COPY broker.entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["broker"]
