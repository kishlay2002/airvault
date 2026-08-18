package validator

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

// Supported file extensions mapped to their types
var supportedTypes = map[string]string{
	".pdf":  "pdf",
	".txt":  "text",
	".md":   "markdown",
	".wav":  "audio",
	".mp3":  "audio",
	".flac": "audio",
	".png":  "image",
	".jpg":  "image",
	".jpeg": "image",
	".tiff": "image",
	".tif":  "image",
}

// DetectFileType returns the VaultMind file type for a given file path.
func DetectFileType(filePath string) (string, error) {
	ext := strings.ToLower(filepath.Ext(filePath))
	fileType, ok := supportedTypes[ext]
	if !ok {
		return "", fmt.Errorf("unsupported extension: %s", ext)
	}
	return fileType, nil
}

// ComputeChecksum computes the SHA-256 checksum of a file.
func ComputeChecksum(filePath string) (string, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	hasher := sha256.New()
	if _, err := io.Copy(hasher, f); err != nil {
		return "", err
	}

	return hex.EncodeToString(hasher.Sum(nil)), nil
}
