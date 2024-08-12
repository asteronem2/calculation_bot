CREATE TABLE IF NOT EXISTS user_table (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    access_level TEXT NOT NULL,
    first_name TEXT,
    username TEXT,
    tracking BOOLEAN DEFAULT FALSE
);


CREATE TABLE IF NOT EXISTS chat_table (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    type TEXT NOT NULL,
    topic INTEGER NOT NULL,
    main_topic INTEGER NOT NULL DEFAULT 0,
    code_name TEXT NOT NULL,
    title TEXT,
    link TEXT,
    locked BOOLEAN NOT NULL DEFAULT TRUE,
    super BOOLEAN NOT NULL DEFAULT TRUE,
    sign BOOLEAN DEFAULT FALSE,
    UNIQUE (chat_id, topic)
);


CREATE TABLE IF NOT EXISTS currency_table (
    id SERIAL PRIMARY KEY,
    chat_pid INTEGER REFERENCES chat_table(id) NOT NULL,
    title TEXT NOT NULL,
    value FLOAT NOT NULL,
    postfix TEXT,
    UNIQUE (chat_pid, title)
);


CREATE TABLE IF NOT EXISTS story_table (
    id SERIAL PRIMARY KEY,
    currency_pid INTEGER REFERENCES currency_table(id) NOT NULL,
    chat_pid INTEGER REFERENCES chat_table(id) DEFAULT NULL,
    user_pid INTEGER REFERENCES user_table(id) NOT NULL,
    expr_type TEXT NOT NULL,
    before_value FLOAT,
    after_value FLOAT NOT NULL,
    message_id INTEGER NOT NULL,
    status BOOLEAN DEFAULT TRUE,
    expression TEXT,
    datetime TIMESTAMPTZ DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS crypto_parsing_table (
    id SERIAL PRIMARY KEY,
    user_pid INTEGER REFERENCES user_table(id) NOT NULL,
    address TEXT NOT NULL,
    min_value FLOAT DEFAULT 0,
    max_value FLOAT DEFAULT 0,
    status BOOLEAN DEFAULT TRUE,
    last_transaction_id TEXT,
    UNIQUE (user_pid, address)
);


CREATE TABLE IF NOT EXISTS callback_addition_table (
    id SERIAL PRIMARY KEY,
    chat_pid INTEGER REFERENCES chat_table(id) NOT NULL,
    user_pid INTEGER REFERENCES user_table(id) NOT NULL,
    got_message_id INTEGER NOT NULL,
    sent_message_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    addition_info TEXT
);


CREATE TABLE IF NOT EXISTS pressure_button_table (
    id SERIAL PRIMARY KEY,
    chat_pid INTEGER REFERENCES chat_table(id) DEFAULT NULL,
    user_pid INTEGER REFERENCES user_table(id) NOT NULL,
    message_id INTEGER NOT NULL,
    callback_data TEXT NOT NULL,
    UNIQUE (user_pid, message_id, callback_data)
);

SET timezone = 'Europe/Moscow';
