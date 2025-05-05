# DocuVault Project: Detailed Explanation

This document provides a detailed explanation of the DocuVault project, covering its architecture, how its components work together, its key features, and its file structure.

## Project Architecture

The DocuVault project is built using a standard client-server architecture.

- **Client (Frontend):** This is what the user interacts with directly through their web browser. It's responsible for presenting the user interface, capturing user input (like login credentials, document details, search queries), and making requests to the backend API.
  - **Technologies Used:** HTML, CSS (primarily Tailwind CSS for styling), and JavaScript.

- **Server (Backend):** This is the core logic of the application. It receives requests from the frontend, processes them, interacts with the database and file storage, enforces business rules (like access control based on roles), and sends responses back to the frontend.
  - **Technologies Used:** Python with the FastAPI framework.

- **Database:** This is where structured data is stored and managed. It holds information about users, documents, and document versions.
  - **Technology Used:** MySQL.

- **File Storage:** This is where the actual document files (PDFs) are stored on the server's file system.

## How DocuVault Works

The workflow in DocuVault generally follows these steps:

1. **User Interaction:** A user interacts with the frontend interface (e.g., clicks a button, fills a form).

2. **Frontend Request:** The JavaScript code in the frontend constructs an HTTP request (e.g., GET, POST) to a specific endpoint on the backend API. This request often includes data (like form data or search queries) and an authentication token (JWT) to identify the user.

3. **Backend Routing and Authentication:** FastAPI receives the request and routes it to the appropriate endpoint function. Authentication middleware verifies the JWT token. If the token is valid, the user's identity and role are determined.

4. **Authorization (Role-Based Access Control):** Endpoint functions use dependencies (like require_role) to check if the authenticated user has the necessary role (user or recruiter) to access that specific resource or perform that action. If not authorized, a 403 Forbidden error is returned.

5. **Business Logic and Database Interaction:** If authorized, the backend function executes the core logic. This often involves:
   - Connecting to the MySQL database using the database.py module.
   - Executing SQL queries to insert, retrieve, update, or delete data (e.g., fetching user details, saving document metadata, getting document versions).
   - Performing file operations (e.g., saving uploaded files to the uploads/ directory, reading file content for search).

6. **Response Generation:** The backend processes the data from the database or file system and formats a response (usually in JSON format) according to the defined Pydantic models.

7. **Frontend Processing:** The frontend receives the response from the backend.

8. **UI Update:** The JavaScript code processes the received data and dynamically updates the HTML content to display the results to the user (e.g., showing a list of documents, displaying search results, showing a success/error message).

## Key Features Explained

### User Authentication (Signup & Login)

- Allows new users and recruiters to register with a username and password.
- Passwords are not stored directly but as secure hash values using passlib[bcrypt].
- Upon successful login, the backend issues a JSON Web Token (JWT) to the frontend.
- This JWT is stored locally in the browser (localStorage) and sent with subsequent requests to authenticate the user.

### Role-Based Access Control

- Users are assigned a role (user or recruiter) during signup.
- Backend endpoints use dependencies (require_role) to ensure only users with the correct role can access specific functionalities (e.g., only user can upload documents, only recruiter can view applicant lists).

### Document Upload

- Users with the user role can upload PDF files.
- The backend handles receiving the file, sanitizing the filename, saving it to the uploads/ directory with a unique name (including version and timestamp).
- It checks if a document with the same title already exists. If so, it creates a new version. If not, it creates a new document entry in the database.
- Document metadata (title, description, owner, latest file path) and version details are stored in the MySQL database.

### Document Management (User)

- Users (user role) can view a list of only the documents they have uploaded.
- For each document, they can see basic details (title, description).
- They can click to view the versions of a specific document.

### Applicant Document Viewing (Recruiter)

- Recruiters (recruiter role) can view a list of all documents uploaded by users with the user role.
- The list displays the document title, description, and importantly, the username of the applicant who owns the document.

### User Listing (Recruiter)

- Recruiters (recruiter role) have access to a list of all registered users who have the user role (i.e., the applicants).

### Document Versioning

- When a user uploads a file with the same title as an existing document they own, it's treated as a new version.
- The backend increments the version number and saves the new file.
- All versions are tracked in the document_versions table.
- The documents table keeps a reference to the latest_file_path.

### Document Download

- Specific document versions can be downloaded.
- Access control ensures only the document owner or a recruiter (if the owner is a user) can download a version.
- The download is handled by the backend serving the file directly, with the frontend using JavaScript (fetchWithAuth) to include the authentication token in the request.

### Document Search

- All authenticated users can search documents.
- The search behavior is role-dependent:
  - Users (user role) search only their own documents.
  - Recruiters (recruiter role) search documents owned by users (user role).
- Search can be performed on document metadata (title and description).
- For recruiters, there is an additional option to search within the content of the document files (currently implemented for PDF and plain text using PyMuPDF).