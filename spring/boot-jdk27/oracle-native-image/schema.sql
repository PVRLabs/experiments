-- MariaDB equivalent of the reduced Market Replay schema; no portfolio tables.
-- UTC is fixed in both guest OS and MariaDB. DATETIME preserves microseconds.
CREATE TABLE quote_samples (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    fetched_at DATETIME(6) NOT NULL,
    cycle INTEGER NOT NULL,
    sample_index INTEGER NOT NULL,
    market_time VARCHAR(5) NOT NULL,
    symbol VARCHAR(8) NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    INDEX idx_quote_samples_symbol_id (symbol, id DESC)
) ENGINE=InnoDB;
