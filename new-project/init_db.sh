#!/bin/sh
# init-db.sh - Initialize SQLite database

set -e

echo "Initializing SQLite database..."

# Create data directory if it doesn't exist
mkdir -p /data

# Create SQLite database if it doesn't exist
if [ ! -f /data/blog.db ]; then
    echo "Creating new SQLite database..."
    
    # Install sqlite3 if not available
    apk add --no-cache sqlite
    
    # Create database with basic tables
    sqlite3 /data/blog.db << 'EOF'
CREATE TABLE IF NOT EXISTS titles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    original_content TEXT NOT NULL,
    suggested_titles TEXT NOT NULL,
    meta_description TEXT,
    keywords TEXT,
    confidence_score REAL,
    serp_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_id ON suggestions(user_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON suggestions(created_at);

-- Insert some sample data if needed
INSERT OR IGNORE INTO titles (title, category) VALUES 
('10 Tips for Better Python Code', 'programming'),
('Machine Learning Basics Explained', 'ai'),
('Web Development Best Practices', 'web');

EOF
    
    echo "Database initialized successfully!"
else
    echo "Database already exists, skipping initialization."
fi

# Ensure proper permissions
chmod 664 /data/blog.db
echo "Database setup complete!"