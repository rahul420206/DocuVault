// static/dashboard.js

// References to navigation tiles
const homeLink = document.getElementById('home-link');
const uploadLink = document.getElementById('upload-link'); // User's own documents upload tile
const documentsLink = document.getElementById('documents-link'); // User's own documents view tile
const searchLink = document.getElementById('search-link');
const logoutLink = document.getElementById('logout-link');
const viewApplicantsLink = document.getElementById('view-applicants-link'); // Recruiters view applicant docs tile
const viewUsersLink = document.getElementById('view-users-link'); // Recruiters view all users tile

// References to content sections
const homeContent = document.getElementById('home-content');
const uploadContent = document.getElementById('upload-content');
const documentsContent = document.getElementById('documents-content');
const searchContent = document.getElementById('search-content');
const viewApplicantsContent = document.getElementById('view-applicants-content');
const viewUsersContent = document.getElementById('view-users-content'); // Content section for viewing users

// References to message and list elements
const messageDiv = document.getElementById('message'); // Main message div
const uploadMessageDiv = document.getElementById('upload-message'); // Specific message div for upload form
const searchResultsList = document.getElementById('search-results') ? document.getElementById('search-results').querySelector('ul') : null; // List for search results (check if element exists)
const applicantsList = document.getElementById('applicants-list') ? document.getElementById('applicants-list').querySelector('ul') : null; // List for applicant documents (check if element exists)
// New: Reference for the Users list - Ensure this element exists in HTML
const usersList = document.getElementById('users-list') ? document.getElementById('users-list').querySelector('ul') : null; // List for all users (check if element exists)


// References to modal elements
const versionsModal = document.getElementById('versions-modal'); // Check if modal exists
// FIX: Simplify the reference to versionsList
const versionsList = document.getElementById('versions-list'); // Directly get the UL element
const closeModal = document.getElementById('close-modal'); // Check if close button exists
const searchContentCheckbox = document.getElementById('search-content-checkbox'); // Check if checkbox exists

// Variables for token and user role
let accessToken = localStorage.getItem('accessToken');
let currentUserRole = null; // Store the user's role

// --- Initialization on DOM Content Loaded ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM fully loaded and parsed."); // Debug log

    const token = localStorage.getItem('accessToken');
    if (!token) {
        // If no token, redirect to login page
        console.log("No access token found, redirecting to login."); // Debug log
        window.location.href = '/';
        return;
    }
    accessToken = token;
    console.log("Access token found.");
    // Fetch user details and role on load
    fetchUserDetails().then(() => {
        // After fetching user details and role, initialize the UI
        console.log("User details fetched, initializing UI based on role."); // Debug log
        initializeUIBasedOnRole();
        showHome(); // Show the default home content
        // Also, ensure the search button state is correct on load if there's a saved query
        const initialQuery = document.getElementById('search-query') ? document.getElementById('search-query').value.trim() : '';
        const searchButton = document.getElementById('search-button');
        if (searchButton) {
            searchButton.disabled = !initialQuery;
        }
    }).catch(error => {
        console.error("Error during initial fetchUserDetails:", error);
        // Handle errors during initial fetch, likely means invalid token
        localStorage.removeItem('accessToken');
        window.location.href = '/';
    });

    // --- Attach Event Listeners ---
    console.log("Attaching event listeners."); // Debug log

    if (homeLink) homeLink.addEventListener('click', showHome);
    else console.warn("homeLink not found."); // Debug log

    // Attach listeners only if the elements exist (based on role visibility set later)
    if (viewApplicantsLink) {
        console.log("Attaching listener to viewApplicantsLink."); // Debug log
        viewApplicantsLink.addEventListener('click', showApplicantDocuments);
    } else console.log("viewApplicantsLink not found (might be hidden by role)."); // Debug log

    if (viewUsersLink) {
        console.log("Attaching listener to viewUsersLink."); // Debug log
        viewUsersLink.addEventListener('click', showUsersList);
    } else console.log("viewUsersLink not found (might be hidden by role)."); // Debug log

    if (uploadLink) { // Check if uploadLink exists (only for users)
        console.log("Attaching listener to uploadLink."); // Debug log
        uploadLink.addEventListener('click', showUpload);
    } else console.log("uploadLink not found (might be hidden by role)."); // Debug log

    if (documentsLink) { // Check if documentsLink exists (only for users)
        console.log("Attaching listener to documentsLink."); // Debug log
        documentsLink.addEventListener('click', showDocuments);
    } else console.log("documentsLink not found (might be hidden by role)."); // Debug log


    if (searchLink) searchLink.addEventListener('click', showSearch);
    else console.warn("searchLink not found."); // Debug log


    // Search form submit listener
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        console.log("Attaching submit listener to searchForm."); // Debug log
        searchForm.addEventListener('submit', showSearch);
    } else console.warn("searchForm not found."); // Debug log


    // Logout link listener
    if (logoutLink) logoutLink.addEventListener('click', () => {
        console.log("Logging out."); // Debug log
        localStorage.removeItem('accessToken');
        window.location.href = '/';
    }); else console.warn("logoutLink not found."); // Debug log


    // Upload form submit listener
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) { // Check if uploadForm exists (only for users)
        console.log("Attaching submit listener to uploadForm."); // Debug log
        uploadForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const description = document.getElementById('description').value;
            const fileInput = document.getElementById('file');
            const messageDiv = uploadMessageDiv;

            if (fileInput.files.length === 0) {
                if (messageDiv) {
                     messageDiv.className = 'error';
                     messageDiv.textContent = 'Please select a file to upload.';
                }
                return;
            }

            const file = fileInput.files[0];
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                 if (messageDiv) {
                     messageDiv.className = 'error'; // Use messageDiv here
                     messageDiv.textContent = 'Please upload a PDF file.';
                 }
                return;
            }
            const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
            if (file.size > MAX_FILE_SIZE) {
                 if (messageDiv) {
                     messageDiv.className = 'error';
                     messageDiv.textContent = `File size exceeds ${MAX_FILE_SIZE / (1024 * 1024)}MB.`;
                 }
                return;
            }

            const formData = new FormData();
            formData.append('description', description);
            formData.append('file', file);

            if (messageDiv) {
                messageDiv.textContent = 'Uploading...';
                messageDiv.className = '';
            }


            try {
                const response = await fetchWithAuth('http://127.0.0.1:8000/documents/', {
                    method: 'POST',
                    body: formData
                });
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`File upload failed: ${response.status} ${response.statusText} - ${errorText}`);
                }
                const data = await response.json();
                if (messageDiv) {
                    messageDiv.className = 'success';
                    messageDiv.textContent = data.message;
                }
                document.getElementById('description').value = '';
                document.getElementById('file').value = '';
                // After successful upload, refresh the user's documents list
                await showDocuments();
            } catch (error) {
                 if (messageDiv) {
                    messageDiv.className = 'error';
                    messageDiv.textContent = `Error: ${error.message}`;
                 }
            }
        });
    } else console.log("uploadForm not found (might be hidden by role)."); // Debug log


    // Modal close handler
    // FIX: Ensure closeModal exists before adding listener
    if (closeModal) {
        console.log("Attaching listener to closeModal."); // Debug log
        closeModal.addEventListener('click', () => {
            if (versionsModal) versionsModal.style.display = 'none';
        });
    } else console.warn("closeModal not found."); // Debug log


    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        if (versionsModal && event.target === versionsModal) {
            versionsModal.style.display = 'none';
        }
    });

    // Enable/disable search button based on query input
    const searchInput = document.getElementById('search-query');
    const searchButton = document.getElementById('search-button');
    if (searchInput && searchButton) { // Check if elements exist
        console.log("Attaching input listener to searchInput."); // Debug log
        searchInput.addEventListener('input', (e) => {
            searchButton.disabled = !e.target.value.trim();
        });
    } else console.warn("searchInput or searchButton not found."); // Debug log


    // Trigger search when the content search checkbox state changes, if there's a query
    const searchContentCheckboxElement = document.getElementById('search-content-checkbox'); // Get reference
    if (searchContentCheckboxElement && searchInput) { // Check if elements exist
        console.log("Attaching change listener to searchContentCheckbox."); // Debug log
        searchContentCheckboxElement.addEventListener('change', () => {
            const query = searchInput.value.trim();
            if (query) {
                showSearch();
            }
        });
    } else console.warn("searchContentCheckbox or searchInput not found."); // Debug log


    // Initial calls are handled in the DOMContentLoaded listener
    // fetchUserDetails() determines the role and calls initializeUIBasedOnRole()
    // initializeUIBasedOnRole() calls showHome()

}); // End DOMContentLoaded listener


// --- Authentication and User Details Fetching ---
async function fetchWithAuth(url, options = {}) {
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${accessToken}`,
        'accept': 'application/json'
    };
    const response = await fetch(url, options);
    if (response.status === 401 || response.status === 403) { // Handle Unauthorized and Forbidden
        console.error(`Access Error (${response.status}) to ${url}: ${response.statusText}`);
        // If unauthorized/forbidden, remove token and redirect to login
        localStorage.removeItem('accessToken');
        window.location.href = '/';
    }
    return response;
}

async function fetchUserDetails() {
    try {
        const response = await fetchWithAuth('http://127.0.0.1:8000/users/me', {
            method: 'GET'
        });
        if (!response.ok) {
            throw new Error(`Failed to fetch user: ${response.statusText}`);
        }
        const user = await response.json();
        currentUserRole = user.role; // Store the user's role
        const userGreetingElement = document.getElementById('user-greeting');
        if (userGreetingElement) {
            userGreetingElement.textContent = `Hi, ${user.username} (${currentUserRole})`; // Display role
        } else {
            console.warn("user-greeting element not found.");
        }
    } catch (error) {
        console.error('Error fetching user details:', error);
        const userGreetingElement = document.getElementById('user-greeting');
        if (userGreetingElement) {
             userGreetingElement.textContent = 'Hi, Guest';
        }
         // If fetching user details fails, assume they are not authenticated correctly
        localStorage.removeItem('accessToken');
        window.location.href = '/';
    }
}

// --- Function to adjust UI based on role ---
function initializeUIBasedOnRole() {
    const isRecruiter = currentUserRole === 'recruiter';
    const isUser = currentUserRole === 'user';
    console.log(`Initializing UI for role: ${currentUserRole}`); // Debug log

    // Hide/Show tiles based on role
    // Only users can upload
    if (uploadLink) {
        uploadLink.style.display = isUser ? 'flex' : 'none';
        console.log(`Upload tile display: ${uploadLink.style.display}`); // Debug log
    } else console.log("uploadLink element not found."); // Debug log

    // Only users see their own docs tile
    if (documentsLink) {
        documentsLink.style.display = isUser ? 'flex' : 'none';
        console.log(`My Documents tile display: ${documentsLink.style.display}`); // Debug log
    } else console.log("documentsLink element not found."); // Debug log

    // Only recruiters see applicant docs tile
    if (viewApplicantsLink) {
        viewApplicantsLink.style.display = isRecruiter ? 'flex' : 'none';
        console.log(`Applicant Docs tile display: ${viewApplicantsLink.style.display}`); // Debug log
    } else console.log("viewApplicantsLink element not found."); // Debug log

    // Only recruiters see View Users tile
    if (viewUsersLink) {
        viewUsersLink.style.display = isRecruiter ? 'flex' : 'none';
        console.log(`View Users tile display: ${viewUsersLink.style.display}`); // Debug log
    } else console.log("viewUsersLink element not found."); // Debug log

    // Search tile is visible to all authenticated users
    if (searchLink) {
        searchLink.style.display = 'flex';
        console.log(`Search tile display: ${searchLink.style.display}`); // Debug log
    } else console.warn("searchLink element not found."); // Debug log


    // Adjust search behavior description if needed (optional)
    // const searchDescription = document.getElementById('search-description'); // Add this ID in HTML
    // if (searchDescription) {
    //     searchDescription.textContent = isUser
    //         ? "Search your own documents by title, description, or content."
    //         : isRecruiter
    //             ? "Search applicant documents by title, description, or content."
    //             : "Search documents."; // Default
    // }
}

// --- Functions to Show Different Content Sections ---
function hideAllContentSections() {
    console.log("Hiding all content sections."); // Debug log
    if (homeContent) homeContent.style.display = 'none';
    if (uploadContent) uploadContent.style.display = 'none';
    if (documentsContent) documentsContent.style.display = 'none';
    if (searchContent) searchContent.style.display = 'none';
    if (viewApplicantsContent) viewApplicantsContent.style.display = 'none';
    if (viewUsersContent) viewUsersContent.style.display = 'none';

    // Clear messages and lists
    if (messageDiv) messageDiv.textContent = '';
    if (uploadMessageDiv) uploadMessageDiv.textContent = '';
    if (searchResultsList) searchResultsList.innerHTML = '';
    if (applicantsList) applicantsList.innerHTML = '';
    if (usersList) usersList.innerHTML = '';
}

function showHome() {
    console.log("Showing Home section."); // Debug log
    hideAllContentSections();
    if (homeContent) homeContent.style.display = 'block';
}

function showUpload() {
    console.log("Showing Upload section."); // Debug log
    hideAllContentSections();
    if (uploadContent) uploadContent.style.display = 'block';
}

async function showDocuments() {
    console.log("Showing My Documents section."); // Debug log
    hideAllContentSections();
    if (documentsContent) documentsContent.style.display = 'block';
    else {
        console.warn("My Documents content section not found."); // Debug log
        return; // Exit if the section doesn't exist for this user
    }


    const documentsList = document.getElementById('documents-list') ? document.getElementById('documents-list').querySelector('ul') : null;
    if (!documentsList) {
         console.error("My Documents list element not found."); // Debug log
         if (messageDiv) {
             messageDiv.className = 'error';
             messageDiv.textContent = "My Documents list display area not available.";
         }
         return; // Exit if list element not found
    }


    documentsList.innerHTML = 'Loading your documents...';

    try {
        // Users fetch their own documents
        const response = await fetchWithAuth('http://127.0.0.1:8000/documents/', {
            method: 'GET'
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch documents: ${response.status} ${response.statusText} - ${errorText}`);
        }
        const data = await response.json();
        console.log('Documents response:', data);

        if (!Array.isArray(data)) {
            throw new Error('Expected an array of documents, but received: ' + JSON.stringify(data));
        }

        documentsList.innerHTML = '';
        if (data.length === 0) {
            documentsList.innerHTML = '<li>No documents found. Try uploading a document!</li>';
        } else {
            data.forEach(doc => {
                // FIX: Check for id existence
                if (!doc || typeof doc !== 'object' || doc.id === undefined || !doc.title) { // Ensure title is also checked
                    console.warn('Invalid document object:', doc); // Debug log
                    return;
                }
                const listItem = document.createElement('li');
                listItem.className = 'document-item';
                // This link currently points to version 1. Consider updating to link to the latest version
                // or always use the "View Versions" button to access downloads.
                listItem.innerHTML = `
                    <span>
                        <a href="/documents/${doc.id}/versions/1/download" target="_blank">${doc.title}</a>
                        - ${doc.description || 'No Description'}
                    </span>
                    <span class="flex items-center gap-2">
                        <button onclick="showVersions(${doc.id}, '${doc.title.replace(/'/g, "\\'")}')">View Versions</button>
                        <button onclick="deleteDocument(${doc.id})" class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md">Delete</button>
                    </span>
                `;
                documentsList.appendChild(listItem);
            });
        }
    } catch (error) {
        console.error('Error fetching documents:', error);
        if (messageDiv) { // Check if messageDiv exists
             messageDiv.className = 'error';
             messageDiv.textContent = error.message.includes('500')
                 ? 'Server error fetching documents. Please try again later.'
                 : `Error fetching documents: ${error.message}`;
        }
        if (documentsList) documentsList.innerHTML = '<li>Failed to load documents.</li>'; // Show error in the list area
    }
}

async function deleteDocument(documentId) {
    console.log(`Attempting to delete document ID: ${documentId}`);

    // Optional: Add a confirmation dialog
    const confirmDelete = confirm("Are you sure you want to delete this document and all its versions? This action cannot be undone.");
    if (!confirmDelete) {
        console.log("Document deletion cancelled by user.");
        return; // Stop if user cancels
    }

    try {
        // Use fetchWithAuth for authenticated DELETE request
        const response = await fetchWithAuth(`http://127.0.0.1:8000/documents/${documentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Deletion failed: ${response.status} ${response.statusText} - ${errorText}`);
        }

        const data = await response.json();
        console.log('Delete response:', data);

        // Show success message
        if (messageDiv) {
            messageDiv.className = 'success';
            messageDiv.textContent = data.message;
        }

        // Refresh the documents list after successful deletion
        await showDocuments();

    } catch (error) {
        console.error('Error during document deletion:', error);
        // Display error message to the user
        if (messageDiv) {
            messageDiv.className = 'error';
            messageDiv.textContent = `Deletion failed: ${error.message}`;
        }
    }
}

// --- Function for Recruiters to show Applicant Documents ---
async function showApplicantDocuments() {
    console.log("Showing Applicant Documents section."); // Debug log
    hideAllContentSections();
    if (viewApplicantsContent) { // Ensure the section exists
        viewApplicantsContent.style.display = 'block';
    } else {
         console.warn("Applicant documents content section not found."); // Debug log
         if (messageDiv) {
              messageDiv.className = 'error';
              messageDiv.textContent = "Applicant documents section not available.";
         }
         return;
    }


    const applicantDocsList = document.getElementById('applicants-list') ? document.getElementById('applicants-list').querySelector('ul') : null; // Use the new list ID
     if (!applicantDocsList) {
          console.error("Applicant documents list element not found."); // Debug log
          if (messageDiv) {
               messageDiv.className = 'error';
               messageDiv.textContent = "Applicant documents list display area not available.";
          }
          return; // Exit if list element not found
     }


    applicantDocsList.innerHTML = 'Loading applicant documents...';

    try {
        // Recruiters fetch documents owned by 'user' roles
        const response = await fetchWithAuth('http://127.0.0.1:8000/documents/applicant/', {
            method: 'GET'
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch applicant documents: ${response.status} ${response.statusText} - ${errorText}`);
        }
        const data = await response.json();
        console.log('Applicant Documents response:', data);

        if (!Array.isArray(data)) {
            throw new Error('Expected an array of documents, but received: ' + JSON.stringify(data));
        }

        applicantDocsList.innerHTML = '';
        if (data.length === 0) {
            applicantDocsList.innerHTML = '<li>No applicant documents found.</li>';
        } else {
            data.forEach(doc => {
                 // Check for required fields including owner_username
                 // FIX: Check for owner_username existence here
                 if (!doc || typeof doc !== 'object' || !doc.title || doc.id === undefined || !doc.owner_username) { // Ensure owner_username is present and id exists
                    console.warn('Invalid document object in applicant documents or missing required fields:', doc); // Debug log
                    // Log the specific invalid document object for debugging
                    console.warn("Invalid document object:", doc);
                    return; // Skip invalid items
                }
                const listItem = document.createElement('li');
                listItem.className = 'document-item';
                 // Recruiters can view/download applicant docs
                 // FIX: Include owner_username in the displayed text
                listItem.innerHTML = `
                    <strong>${doc.owner_username}</strong>: ${doc.title} - ${doc.description || 'No Description'}
                    <button onclick="showVersions(${doc.id}, '${doc.title.replace(/'/g, "\\'")}')">View Versions</button>
                `;
                applicantDocsList.appendChild(listItem);
            });
        }
    } catch (error) {
        console.error('Error fetching applicant documents:', error); // Debug log
        if (messageDiv) { // Check if messageDiv exists
             messageDiv.className = 'error';
             messageDiv.textContent = error.message.includes('500')
                ? 'Server error fetching applicant documents. Please try again later.'
                : `Error fetching applicant documents: ${error.message}`;
        }
        if (applicantDocsList) applicantDocsList.innerHTML = '<li>Failed to load applicant documents.</li>'; // Show error in the list area
    }
}

// --- New function for Recruiters to show the list of Users ---
async function showUsersList() {
     console.log("Showing View Users section."); // Debug log
     hideAllContentSections();
     if (viewUsersContent) { // Ensure the section exists
         viewUsersContent.style.display = 'block';
     } else {
         console.warn("View users content section not found."); // Debug log
         if (messageDiv) { // Check if messageDiv exists
              messageDiv.className = 'error';
              messageDiv.textContent = "View users section not available.";
         }
         return;
     }

     // FIX: Ensure usersList is not null before using it
     if (!usersList) {
          console.error("Users list element not found in HTML."); // Debug log
          if (messageDiv) {
               messageDiv.className = 'error';
               messageDiv.textContent = "Users list display area not available.";
          }
          return;
     }


     usersList.innerHTML = 'Loading users...'; // Use the new usersList reference

     try {
         console.log("Attempting to fetch users from /users/"); // Debug log
         // Recruiters fetch all users
         const response = await fetchWithAuth('http://127.0.0.1:8000/users/', {
             method: 'GET'
         });

         console.log("Response status for /users/:", response.status); // Debug log

         if (!response.ok) {
             const errorText = await response.text();
             console.error("Error response text:", errorText); // Debug log
             throw new Error(`Failed to fetch users: ${response.status} ${response.statusText} - ${errorText}`);
         }
         const data = await response.json();
         console.log('Users list response data:', data); // Debug log

         if (!Array.isArray(data)) {
             console.error('Unexpected users list format:', data); // Debug log
             throw new Error('Expected an array of users, but received: ' + JSON.stringify(data));
         }

         usersList.innerHTML = ''; // Clear loading indicator
         if (data.length === 0) {
             usersList.innerHTML = '<li>No users found.</li>';
         } else {
             data.forEach(user => {
                  // FIX: Check for required fields including role and id existence
                  if (!user || typeof user !== 'object' || !user.username || user.id === undefined || user.role === undefined) {
                     console.warn('Invalid user object in users list or missing required fields:', user); // Debug log
                     return;
                 }
                 const listItem = document.createElement('li');
                 // Display user info
                 listItem.textContent = `ID: ${user.id}, Username: ${user.username}, Role: ${user.role}`;
                 // Optionally add a button or link to view their documents directly from here
                 // e.g., <button onclick="showApplicantDocumentsForUser(${user.id})">View Docs</button>
                 usersList.appendChild(listItem);
             });
         }

     } catch (error) {
         console.error('Error fetching users:', error); // Debug log
         if (messageDiv) { // Check if messageDiv exists
              messageDiv.className = 'error';
              messageDiv.textContent = error.message.includes('500')
                 ? 'Server error fetching users. Please try again later.'
                 : `Error fetching users: ${error.message}`;
         }
         // FIX: Ensure usersList is not null before setting innerHTML
         if (usersList) {
             usersList.innerHTML = '<li>Failed to load users.</li>'; // Show error in the list area
         }
     }
}


async function showSearch(event) {
    if (event && event.preventDefault) {
        event.preventDefault();
    }
    console.log("Showing Search section."); // Debug log

    hideAllContentSections();
    if (searchContent) searchContent.style.display = 'block';
    else {
        console.warn("Search content section not found."); // Debug log
        return; // Exit if section doesn't exist
    }


    if (!searchResultsList) {
        console.error("Search results list element not found."); // Debug log
        if (messageDiv) {
             messageDiv.className = 'error';
             messageDiv.textContent = "Search results display area not available.";
        }
        return; // Exit if list element not found
    }


    searchResultsList.innerHTML = '';

    const queryInput = document.getElementById('search-query');
    const query = queryInput ? queryInput.value.trim() : '';

    const isSearchingContent = searchContentCheckbox ? searchContentCheckbox.checked : false;


    if (!query) {
        searchResultsList.innerHTML = '<li>Please enter a search query.</li>';
        return;
    }

    searchResultsList.innerHTML = '<li>Searching...'; // Indicate searching

    let url = `http://127.0.0.1:8000/documents/search/?query=${encodeURIComponent(query)}`;
    if (isSearchingContent) {
        url += `&search_content=true`;
    }

    try {
        const response = await fetchWithAuth(url, {
            method: 'GET'
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Search failed: ${response.status} ${response.statusText} - ${errorText}`);
        }
        const data = await response.json();
        console.log('Search response:', data);

        // FIX: Check for data.results being an array
        if (!data || !Array.isArray(data.results)) {
             console.error('Unexpected search results format:', data); // Debug log
             if (searchResultsList) searchResultsList.innerHTML = '<li>Error: Received unexpected data format.</li>';
             return;
        }

        searchResultsList.innerHTML = ''; // Clear loading or previous results
        if (data.results.length === 0) {
            searchResultsList.innerHTML = `<li>No matching documents found for "${query}"${isSearchingContent ? ' in content or metadata' : ' in metadata'}.</li>`;
        } else {
            data.results.forEach(doc => {
                // Check for required fields including owner_username for recruiters
                // Assuming search results for recruiters also include owner_username
                 const isRecruiter = currentUserRole === 'recruiter';
                 // FIX: Check for owner_username existence for recruiters and id existence for all
                 if (!doc || typeof doc !== 'object' || !doc.title || doc.id === undefined || (isRecruiter && !doc.owner_username)) {
                    console.warn('Invalid document object in search results or missing required fields:', doc); // Debug log
                    // Log the specific invalid document object for debugging
                    console.warn("Invalid document object:", doc);
                    return; // Skip invalid items
                }
                const listItem = document.createElement('li');
                listItem.className = 'document-item';
                 // Links/buttons should work for both users (their own docs) and recruiters (applicant docs)
                 // FIX: Include owner_username in the displayed text for recruiters
                 // Use the username variable defined below
                 const username = isRecruiter ? (doc.owner_username || 'Unknown User') : ''; // Get username or default
                 const displayTitle = isRecruiter && username ? `<strong>${username}</strong>: ${doc.title}` : doc.title;

                listItem.innerHTML = `
                    ${displayTitle} - ${doc.description || 'No Description'}
                    <button onclick="showVersions(${doc.id}, '${doc.title.replace(/'/g, "\\'")}')">View Versions</button>
                `;
                searchResultsList.appendChild(listItem);
            });
        }
    } catch (error) {
        console.error('Error searching documents:', error); // Debug log
        if (searchResultsList) searchResultsList.innerHTML = `<li class="error">Error: ${error.message}</li>`; // Show error in the list area
    }
}

async function showVersions(documentId, documentTitle) {
    console.log(`Showing versions for document ID: ${documentId}`); // Debug log
    try {
        const response = await fetchWithAuth(`http://127.0.0.1:8000/documents/${documentId}/versions/`, {
            method: 'GET'
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch versions: ${response.status} ${response.statusText} - ${errorText}`);
        }
        const data = await response.json();
        console.log('Versions response:', data);

        // FIX: Check for data.versions being an array
        if (!data || !Array.isArray(data.versions)) {
            console.error('Expected an array of versions, but received: ' + JSON.stringify(data)); // Debug log
            if (versionsList) versionsList.innerHTML = '<li>Error: Received unexpected data format for versions.</li>';
             if (versionsModal) versionsModal.style.display = 'block'; // Still show modal to display error
            return;
        }

        // FIX: Check if versionsList exists after getting data
        if (!versionsList) {
            console.error("Versions list element not found."); // Debug log
            if (messageDiv) {
                 messageDiv.className = 'error';
                 messageDiv.textContent = "Versions list display area not available.";
            }
             // Still show modal even if list element is missing, to show error message
             if (versionsModal) versionsModal.style.display = 'block';
            return;
        }


        versionsList.innerHTML = `<h4>Versions for ${documentTitle}</h4>`;
        if (data.versions.length === 0) {
            versionsList.innerHTML += '<li>No versions found.</li>';
        } else {
            data.versions.forEach(version => {
                 // FIX: Check for required fields in version object
                 if (!version || typeof version !== 'object' || version.version === undefined || !version.uploaded_at || !version.file_path) { // Check for file_path too
                     console.warn('Invalid version object or missing required fields:', version); // Debug log
                     return; // Skip invalid items
                 }
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    Version ${version.version} (Uploaded: ${new Date(version.uploaded_at).toLocaleString()})
                    <button onclick="downloadVersion(${documentId}, ${version.version}, '${documentTitle.replace(/'/g, "\\'")}')">Download</button>
                `;
                versionsList.appendChild(listItem);
            });
        }
         if (versionsModal) versionsModal.style.display = 'block'; // Show the modal
    } catch (error) {
        console.error('Error fetching versions:', error); // Debug log
        if (messageDiv) { // Check if messageDiv exists
             messageDiv.className = 'error';
             messageDiv.textContent = `Error fetching versions: ${error.message}`;
        }
         // FIX: Ensure versionsList is not null before setting innerHTML
         if (versionsList) {
            versionsList.innerHTML = `<li>Failed to load versions.</li>`; // Show error in the list area
         }
         if (versionsModal) versionsModal.style.display = 'block'; // Still show modal to display error
    }
}

// New function to handle authenticated download
async function downloadVersion(documentId, versionNumber, documentTitle) {
    console.log(`Attempting to download document ID ${documentId}, version ${versionNumber}`);
    const downloadUrl = `http://127.0.0.1:8000/documents/${documentId}/versions/${versionNumber}/download`;

    try {
        const response = await fetchWithAuth(downloadUrl, {
            method: 'GET'
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Download failed: ${response.status} ${response.statusText} - ${errorText}`);
        }

        // Get the filename from the Content-Disposition header if available,
        // otherwise construct one.
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${documentTitle}_v${versionNumber}.pdf`; // Default filename
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1];
            }
        }

        // Get the blob data
        const blob = await response.blob();

        // Create a temporary URL for the blob
        const url = window.URL.createObjectURL(blob);

        // Create a temporary link element to trigger the download
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename; // Set the download filename

        // Append the link to the body and click it
        document.body.appendChild(a);
        a.click();

        // Clean up the temporary URL and link element
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log(`Download of ${filename} successful.`);

    } catch (error) {
        console.error('Error during download:', error);
        // Display error message to the user (e.g., in the messageDiv or modal)
        if (messageDiv) {
            messageDiv.className = 'error';
            messageDiv.textContent = `Download failed: ${error.message}`;
        }
         // Optionally display error in the modal as well
         if (versionsList) { // Check if versionsList exists
             const errorItem = document.createElement('li');
             errorItem.className = 'error';
             errorItem.textContent = `Download failed for version ${versionNumber}: ${error.message}`;
             versionsList.appendChild(errorItem);
         }
    }
}


// --- Modal and Search Input Listeners ---

// Modal close handler
// FIX: Ensure closeModal exists before adding listener
if (closeModal) {
    closeModal.addEventListener('click', () => {
        if (versionsModal) versionsModal.style.display = 'none';
    });
}


// Close modal when clicking outside
window.addEventListener('click', (event) => {
    if (versionsModal && event.target === versionsModal) {
        versionsModal.style.display = 'none';
    }
});

// Enable/disable search button based on query input
const searchInput = document.getElementById('search-query');
const searchButton = document.getElementById('search-button');
if (searchInput && searchButton) { // Check if elements exist
    searchInput.addEventListener('input', (e) => {
        searchButton.disabled = !e.target.value.trim();
    });
}


// Trigger search when the content search checkbox state changes, if there's a query
const searchContentCheckboxElement = document.getElementById('search-content-checkbox'); // Get reference
if (searchContentCheckboxElement && searchInput) { // Check if elements exist
    searchContentCheckboxElement.addEventListener('change', () => {
        const query = searchInput.value.trim();
        if (query) {
            showSearch();
        }
    });
}


// Initial calls are handled in the DOMContentLoaded listener
// fetchUserDetails() determines the role and calls initializeUIBasedOnRole()
// initializeUIBasedOnRole() calls showHome()
