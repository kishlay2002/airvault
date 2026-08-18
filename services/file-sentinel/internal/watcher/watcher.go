package watcher

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/fsnotify/fsnotify"
	"github.com/rs/zerolog/log"
	"github.com/vaultmind/file-sentinel/internal/queue"
	"github.com/vaultmind/file-sentinel/internal/validator"
)

// Watcher monitors a directory for new files and enqueues ingestion jobs.
type Watcher struct {
	watchDir string
	queue    *queue.RedisQueue
}

// New creates a new file watcher.
func New(watchDir string, q *queue.RedisQueue) *Watcher {
	return &Watcher{
		watchDir: watchDir,
		queue:    q,
	}
}

// Start begins watching the directory for new files.
func (w *Watcher) Start() error {
	// Ensure watch directory exists
	if err := os.MkdirAll(w.watchDir, 0755); err != nil {
		return err
	}

	fsWatcher, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	defer fsWatcher.Close()

	if err := fsWatcher.Add(w.watchDir); err != nil {
		return err
	}

	log.Info().Str("directory", w.watchDir).Msg("file sentinel started")

	for {
		select {
		case event, ok := <-fsWatcher.Events:
			if !ok {
				return nil
			}
			if event.Has(fsnotify.Create) {
				w.handleNewFile(event.Name)
			}

		case err, ok := <-fsWatcher.Errors:
			if !ok {
				return nil
			}
			log.Error().Err(err).Msg("watcher error")
		}
	}
}

func (w *Watcher) handleNewFile(filePath string) {
	filename := filepath.Base(filePath)

	// Skip hidden files and temp files
	if strings.HasPrefix(filename, ".") || strings.HasSuffix(filename, ".tmp") {
		return
	}

	// Validate file type
	fileType, err := validator.DetectFileType(filePath)
	if err != nil {
		log.Warn().Str("file", filename).Err(err).Msg("unsupported file type")
		return
	}

	// Compute checksum
	checksum, err := validator.ComputeChecksum(filePath)
	if err != nil {
		log.Error().Str("file", filename).Err(err).Msg("checksum computation failed")
		return
	}

	// Get file size
	info, err := os.Stat(filePath)
	if err != nil {
		log.Error().Str("file", filename).Err(err).Msg("stat failed")
		return
	}

	// Enqueue
	job := queue.IngestionJob{
		FilePath: filePath,
		FileType: fileType,
		Checksum: checksum,
		FileSize: info.Size(),
	}

	if err := w.queue.Enqueue(job); err != nil {
		log.Error().Str("file", filename).Err(err).Msg("enqueue failed")
		return
	}

	log.Info().
		Str("file", filename).
		Str("type", fileType).
		Str("checksum", checksum[:16]+"...").
		Int64("size", info.Size()).
		Msg("file enqueued for ingestion")
}
