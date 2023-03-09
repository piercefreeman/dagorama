FROM golang:alpine AS builder

ENV PORT=50051

COPY broker /broker

RUN cd /broker && go mod download
RUN cd /broker && go build .

FROM alpine:3 AS broker

COPY --from=builder /broker/dagorama /broker
COPY broker.entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["broker"]
