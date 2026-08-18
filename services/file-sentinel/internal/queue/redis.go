package queue

import (
	"context"
	"encoding/json"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
)

const queueKey = "vaultmind:ingestion:queue"

// IngestionJob represents a file to be ingested.
type IngestionJob struct {
	JobID      string `json:"job_id"`
	FilePath   string `json:"file_path"`
	FileType   string `json:"file_type"`
	Checksum   string `json:"checksum"`
	FileSize   int64  `json:"file_size"`
	EnqueuedAt string `json:"enqueued_at"`
}

// RedisQueue manages the ingestion job queue.
type RedisQueue struct {
	client *redis.Client
}

// NewRedisQueue creates a new Redis queue.
func NewRedisQueue(redisURL string) (*RedisQueue, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, err
	}

	client := redis.NewClient(opts)

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, err
	}

	log.Info().Str("url", redisURL).Msg("connected to Redis")
	return &RedisQueue{client: client}, nil
}

// Enqueue adds an ingestion job to the queue.
func (q *RedisQueue) Enqueue(job IngestionJob) error {
	job.EnqueuedAt = time.Now().UTC().Format(time.RFC3339)

	if job.JobID == "" {
		job.JobID = generateJobID()
	}

	data, err := json.Marshal(job)
	if err != nil {
		return err
	}

	ctx := context.Background()
	return q.client.RPush(ctx, queueKey, string(data)).Err()
}

// Close closes the Redis connection.
func (q *RedisQueue) Close() error {
	return q.client.Close()
}

func generateJobID() string {
	return time.Now().Format("20060102-150405.000")
}
