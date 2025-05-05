# 📁 DocuVault Project: Detailed Explanation

This document provides a detailed explanation of the **DocuVault** project, covering its architecture, how its components work together, its key features, and its file structure.

---

## 🏗️ Project Architecture

DocuVault is built using a **standard client-server architecture** with the following main components:

### 🔹 Client (Frontend)

- **Role**: User interface and interaction layer  
- **Responsibilities**:
  - Displaying forms, lists, and navigation
  - Capturing user inputs (e.g., login, upload)
  - Making requests to the backend API

- **Technologies Used**:  
  - `HTML`  
  - `CSS` (with **Tailwind CSS**)  
  - `JavaScript`

---

### 🔸 Server (Backend)

- **Role**: Core logic and API layer  
- **Responsibilities**:
  - Handling HTTP requests (GET, POST, etc.)
  - Authenticating and authorizing users
  - Managing document upload/download/versioning
  - Communicating with the database and file system

- **Technology Used**:  
  - `Python` with **FastAPI**

---

### 🗃️ Database

- **Role**: Stores and manages structured data  
- **Technology Used**:  
  - `MySQL`

- **Data Stored**:
  - User credentials (hashed)
  - User roles
  - Document metadata
  - Document version history

---

### 📂 File Storage

- **Role**: Stores actual PDF document files on the server
- **Location**: Organized directory on server's file system

---

## 🔄 How DocuVault Works: Workflow Breakdown

### 1. 🧑 User Interaction

- Users (applicants or recruiters) interact with the web UI to perform actions (e.g., login, upload a resume).

### 2. 🌐 Frontend Request

- JavaScript constructs HTTP requests (e.g., `POST /upload`, `GET /documents`)
- Requests include form data and a **JWT token** for authentication

### 3. 🛠️ Backend Processing

- **FastAPI** receives and routes requests to endpoint functions
- Middleware validates JWT and extracts user info

### 4. 🔐 Authorization

- Custom FastAPI dependencies (e.g., `require_role`) check whether the user has permission to access the requested resource

### 5. 🗃️ Data Handling

- If valid, backend:
  - Interacts with MySQL DB to fetch/store metadata
  - Saves uploaded files to the server's file system
  - Returns a response (JSON) to the frontend

---

## 🌟 Key Features

- ✅ **User Authentication** with JWT (login/signup)
- 🔐 **Role-Based Access Control** (users vs. recruiters)
- 📤 **Document Uploading** (PDF only)
- 📑 **Version Control** for documents
- 🔎 **Recruiter Search** & document download
- 👥 **User Listing** for recruiters

---

## 🚀 Future Improvements (Optional)

- 🧾 Email verification and password reset
- 📊 Dashboard analytics for recruiters
- 🔒 Encrypted file storage
- ☁️ Cloud deployment

---

## 📬 Contact

For queries or suggestions, feel free to [open an issue](https://github.com/rahul420206/task/issues) or contact the maintainer.

---

