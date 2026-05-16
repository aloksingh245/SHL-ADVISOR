# SHL Advisor Frontend (React)

This is a modular React 18 application built for the SHL Assessment Recommender system.

## Project Structure

- `src/components/`: Contains all UI components (Header, Chat, Input, Cards).
- `src/styles/`: Contains the global CSS variables and component styles.
- `src/App.js`: Main logic for stateless conversation history management and API communication.

## Getting Started

1.  **Ensure the Backend is running**:
    ```bash
    uvicorn app.main:app --host 127.0.0.1 --port 8001
    ```

2.  **Install dependencies**:
    ```bash
    cd frontend
    npm install
    ```

3.  **Run the application**:
    ```bash
    npm start
    ```

The application will be available at `http://localhost:3000`.

## Features

- **Stateless sync**: Automatically passes the full `messages[]` array to the backend.
- **Dynamic Cards**: Renders SHL product recommendations as scannable cards.
- **Modern UI**: Built with Inter font and SHL brand colors.
