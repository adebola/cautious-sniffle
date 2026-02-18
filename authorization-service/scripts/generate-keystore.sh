#!/usr/bin/env bash
set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <storepass> <keypass>"
    echo "  storepass - Password for the PKCS12 keystore"
    echo "  keypass   - Password for the private key"
    exit 1
fi

STOREPASS="$1"
KEYPASS="$2"

echo "Store password: ${STOREPASS}"
echo "Key password:   ${KEYPASS}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/../src/main/resources/keys"
OUTPUT_FILE="${OUTPUT_DIR}/jwt-keystore.p12"

mkdir -p "${OUTPUT_DIR}"

keytool -genkeypair \
    -alias authserver \
    -keyalg RSA \
    -keysize 2048 \
    -sigalg SHA256withRSA \
    -storetype PKCS12 \
    -keystore "${OUTPUT_FILE}" \
    -storepass "${STOREPASS}" \
    -keypass "${KEYPASS}" \
    -dname "CN=ChatCraft JWT Signing Key" \
    -validity 3650

echo "Keystore generated at: ${OUTPUT_FILE}"
