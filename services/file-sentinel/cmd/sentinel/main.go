package main

import (
	"os"
	"os/signal"
	"syscall"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/vaultmind/file-sentinel/internal/queue"
	"github.com/vaultmind/file-sentinel/internal/watcher"
)

func main() {
	// Structured JSON logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	logLevel := os.Getenv("LOG_LEVEL")
	if logLevel == "debug" {
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	} else {
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	}
	log.Logger = zerolog.New(os.Stdout).With().Timestamp().Str("service", "file-sentinel").Logger()

	// Config from env
	watchDir := os.Getenv("WATCH_DIR")
	if watchDir == "" {
		watchDir = "/data/inbox"
	}

	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "redis://localhost:6379/0"
	}

	// Connect to Redis
	q, err := queue.NewRedisQueue(redisURL)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to Redis")
	}
	defer q.Close()

	// Start watcher in goroutine
	w := watcher.New(watchDir, q)

	go func() {
		if err := w.Start(); err != nil {
			log.Fatal().Err(err).Msg("watcher failed")
		}
	}()

	// Wait for shutdown signal
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh

	log.Info().Str("signal", sig.String()).Msg("shutting down")
}
