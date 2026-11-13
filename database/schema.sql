BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE users (
    id VARCHAR(32) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    name VARCHAR(120) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE projects (
    id VARCHAR(32) NOT NULL, 
    user_id VARCHAR(32) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    source_type VARCHAR(10) NOT NULL, 
    source_url TEXT, 
    source_key VARCHAR(512), 
    original_filename VARCHAR(255) NOT NULL, 
    file_size BIGINT NOT NULL, 
    format VARCHAR(64) NOT NULL, 
    duration FLOAT NOT NULL, 
    width INTEGER NOT NULL, 
    height INTEGER NOT NULL, 
    fps FLOAT NOT NULL, 
    orientation VARCHAR(20) NOT NULL, 
    has_audio BOOLEAN NOT NULL, 
    thumbnail_key VARCHAR(512), 
    split_mode VARCHAR(10) NOT NULL, 
    split_seconds INTEGER NOT NULL, 
    language VARCHAR(32) NOT NULL, 
    mood TEXT NOT NULL, 
    visual_style TEXT NOT NULL, 
    summary TEXT NOT NULL, 
    prompt_language VARCHAR(32) NOT NULL, 
    prompt_style VARCHAR(64) NOT NULL, 
    global_prompt TEXT NOT NULL, 
    storage_bytes BIGINT NOT NULL, 
    error TEXT NOT NULL, 
    rights_confirmed_at TIMESTAMP WITH TIME ZONE, 
    source_expires_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_projects_status ON projects (status);

CREATE INDEX ix_projects_user_id ON projects (user_id);

CREATE TABLE analysis_steps (
    id VARCHAR(32) NOT NULL, 
    project_id VARCHAR(32) NOT NULL, 
    key VARCHAR(32) NOT NULL, 
    position INTEGER NOT NULL, 
    status VARCHAR(12) NOT NULL, 
    progress FLOAT NOT NULL, 
    message TEXT NOT NULL, 
    error TEXT NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE, 
    finished_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_analysis_steps_project_id ON analysis_steps (project_id);

CREATE TABLE characters (
    id VARCHAR(32) NOT NULL, 
    project_id VARCHAR(32) NOT NULL, 
    index INTEGER NOT NULL, 
    label VARCHAR(64) NOT NULL, 
    data JSON NOT NULL, 
    prompt_descriptor TEXT NOT NULL, 
    descriptors JSON NOT NULL, 
    scene_indexes JSON NOT NULL, 
    reference_key VARCHAR(512), 
    reference_frame_id VARCHAR(32), 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_characters_project_id ON characters (project_id);

CREATE TABLE dialogue_lines (
    id VARCHAR(32) NOT NULL, 
    project_id VARCHAR(32) NOT NULL, 
    scene_index INTEGER, 
    start FLOAT NOT NULL, 
    "end" FLOAT NOT NULL, 
    text TEXT NOT NULL, 
    language VARCHAR(32) NOT NULL, 
    character_index INTEGER, 
    tone VARCHAR(255) NOT NULL, 
    emotion VARCHAR(255) NOT NULL, 
    intensity VARCHAR(255) NOT NULL, 
    pace VARCHAR(255) NOT NULL, 
    identifiable BOOLEAN NOT NULL, 
    confidence FLOAT, 
    edited BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_dialogue_lines_project_id ON dialogue_lines (project_id);

CREATE TABLE scenes (
    id VARCHAR(32) NOT NULL, 
    project_id VARCHAR(32) NOT NULL, 
    index INTEGER NOT NULL, 
    start FLOAT NOT NULL, 
    "end" FLOAT NOT NULL, 
    target_duration FLOAT, 
    selected BOOLEAN NOT NULL, 
    data JSON NOT NULL, 
    character_indexes JSON NOT NULL, 
    description TEXT NOT NULL, 
    prompt_sections JSON NOT NULL, 
    prompt_text TEXT NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_scenes_project_id ON scenes (project_id);

CREATE TABLE frames (
    id VARCHAR(32) NOT NULL, 
    project_id VARCHAR(32) NOT NULL, 
    scene_id VARCHAR(32) NOT NULL, 
    kind VARCHAR(16) NOT NULL, 
    timestamp FLOAT NOT NULL, 
    key VARCHAR(512) NOT NULL, 
    width INTEGER NOT NULL, 
    height INTEGER NOT NULL, 
    sharpness FLOAT NOT NULL, 
    is_representative BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
    FOREIGN KEY(scene_id) REFERENCES scenes (id) ON DELETE CASCADE
);

CREATE INDEX ix_frames_project_id ON frames (project_id);

CREATE INDEX ix_frames_scene_id ON frames (scene_id);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

COMMIT;

