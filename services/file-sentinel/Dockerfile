# VaultMind File Sentinel — Go multi-stage build
# Produces a ~5MB statically-linked binary. No runtime dependencies.

FROM golang:1.22-alpine AS builder

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /sentinel ./cmd/sentinel

FROM scratch

COPY --from=builder /sentinel /sentinel

ENTRYPOINT ["/sentinel"]
