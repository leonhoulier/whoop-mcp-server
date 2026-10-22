#!/bin/sh
set -eu
umask 077
directory=/var/backups/whoop-mcp
install -d -m 700 "$directory"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$directory/whoop-$stamp.tar.gz"
tar --exclude=owner.lock -czf "$archive.tmp" -C /var/lib whoop-mcp
mv "$archive.tmp" "$archive"
find "$directory" -maxdepth 1 -type f -name 'whoop-*.tar.gz' -mtime +14 -delete
