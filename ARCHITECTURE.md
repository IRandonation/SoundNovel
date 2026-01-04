# Architecture and Technical Details

## Overview

SoundNovel is an AI-assisted novel writing agent designed to automate the pipeline from core settings to a complete novel draft. It leverages multiple Large Language Models (LLMs) to ensure logical consistency, plot progression, and stylistic coherence across long narratives.

## System Architecture

The system is organized into a modular architecture:

### 1. Core Package (`novel_generator/`)

This is the heart of the application, containing the business logic and core functionalities.

- **`core/`**:
  - **`project_manager.py`**: Orchestrates the initialization and validation of the project structure.
  - **`outline_generator.py`**: Handles the generation of chapter outlines from the overall outline and core settings.
  - **`batch_outline_generator.py`**: Manages the bulk generation of outlines, handling pagination and context.
  - **`chapter_expander.py`**: Responsible for expanding chapter outlines into full drafts, ensuring adherence to style guides.
  - **`sliding_window.py`**: Implements the sliding window context mechanism to maintain continuity across chapters.

- **`utils/`**:
  - **`multi_model_client.py`**: A robust client for interacting with various LLM providers (ZhipuAI, Doubao, Ark). It handles model routing, retries, and fallbacks.
  - **`file_handler.py`**: Utilities for safe file reading, writing, and backup management.
  - **`logger.py`**: centralized logging configuration.

- **`config/`**:
  - **`settings.py`**: Defines configuration schemas (using dataclasses) for API keys, paths, and generation parameters.

### 2. Interface Layer

- **CLI (`05_script/main.py`)**: The command-line interface for running the generation pipeline (init, outline, expand).
- **GUI (`gui_app.py`)**: A Streamlit-based graphical user interface for a more interactive experience.
- **Scripts (`05_script/`)**:
  - `expand_chapters.py`: Standalone script for expanding specific chapters or ranges.
  - `merge_drafts.py`: Utility to merge generated drafts into a single manuscript.

### 3. Data Flow

1.  **Input**: User provides `core_setting.yaml` (world-building, characters) and `overall_outline.yaml` (plot beats).
2.  **Outline Generation**: The system breaks down the overall outline into chapter-level outlines (`02_outline/`).
3.  **Expansion**: Using a sliding window context (previous N chapters' summaries), the system expands each chapter outline into a draft (`03_draft/`).
4.  **Output**: Drafts are merged into a final document (`07_output/`).

## Technical Key Points

### Sliding Window Context
To solve the context limit problem in long novels, the system uses a sliding window approach. When generating Chapter N, it feeds the summaries and key events of Chapters N-k to N-1 into the model. This ensures the AI remembers immediate history without exceeding token limits.

### Multi-Model Strategy
The system supports switching between different models for different tasks:
- **Logic/Planning**: Uses "Long" context models (e.g., GLM-4-Long) for high-level outlining and consistency checks.
- **Drafting**: Uses faster, cost-effective models (e.g., GLM-4.5-Flash) for text expansion.

### Error Handling & Recovery
- **API Retries**: Built-in exponential backoff for API failures.
- **State Preservation**: Progress is saved after each chapter. If a batch fails, it can resume from the last successful chapter.
- **Backups**: Every overwrite operation triggers an automatic backup to `_history/` folders.

## Directory Structure Rationale

- **`01_source/`**: Human-written creative input.
- **`02_outline/`**: AI-generated structural intermediate.
- **`03_draft/`**: AI-generated raw content.
- **`04_prompt/`**: Prompt engineering templates.
- **`05_script/`**: Operational scripts.
- **`06_log/`**: Observability and debugging.

## Security & Privacy

- **Sensitive Data**: API keys are stored in `05_script/config.json`, which is git-ignored.
- **Environment**: Support for `.env` files and environment variables.
- **Logs**: API logs are separated to avoid accidental exposure of content in system logs (though content logging should be disabled in production).
