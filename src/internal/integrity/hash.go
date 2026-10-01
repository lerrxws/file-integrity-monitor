package integrity

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
)

func CalculateSHA256(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}

	hash := sha256.Sum256(data)

	return hex.EncodeToString(hash[:]), nil
}
