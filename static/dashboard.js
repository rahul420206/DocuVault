const homeLink = document.getElementById('home-link');
const uploadLink = document.getElementById('upload-link');
const documentsLink = document.getElementById('documents-link');
const searchLink = document.getElementById('search-link');
const logoutLink = document.getElementById('logout-link');

const homeContent = document.getElementById('home-content');
const uploadContent = document.getElementById('upload-content');
const documentsContent = document.getElementById('documents-content');
const searchContent = document.getElementById('search-content');
const messageDiv = document.getElementById('message');
const userGreeting = document.getElementById('user-greeting');
const versionsModal = document.getElementById('versions-modal');
const versionsList = document.getElementById('versions-list');
const closeModal = document.getElementById('close-modal');

let accessToken = localStorage.getItem('accessToken');
let currentUsername = 'Guest';

if (!accessToken) {
    window.location.href = '/';
}

async function fetchWithAuth(url, options = {}) {
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${accessToken}`,
        'accept': 'application/json'
    };
    const response = await fetch(url, options);
    if (response.status === 401) {
        console.error(`Unauthorized request to ${url}: ${response.statusText}`);
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
        currentUsername = user.username;
        userGreeting.textContent = `Hi, ${currentUsername}`;
    } catch (error) {
        console.error('Error fetching user details:', error);
        userGreeting.textContent = 'Hi, Guest';
    }
}

function showHome() {
    homeContent.style.display = 'block';
    uploadContent.style.display = 'none';
    documentsContent.style.display = 'none';
    searchContent.style.display = 'none';
    messageDiv.textContent = '';
}

function showUpload() {
    homeContent.style.display = 'none';
    uploadContent.style.display = 'block';
    documentsContent.style.display = 'none';
    searchContent.style.display = 'none';
    messageDiv.textContent = '';
}

async function showDocuments() {
    homeContent.style.display = 'none';
    uploadContent.style.display = 'none';
    documentsContent.style.display = 'block';
    searchContent.style.display = 'none';
    messageDiv.textContent = '';

    const documentsList = document.getElementById('documents-list').querySelector('ul');
    documentsList.innerHTML = 'Loading...';

    try {
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
            documentsList.innerHTML = 'No documents found. Try uploading a document!';
        } else {
            data.forEach(doc => {
                if (!doc || typeof doc !== 'object' || !doc.title || !doc.id) {
                    console.warn('Invalid document object:', doc);
                    return;
                }
                const listItem = document.createElement('li');
                listItem.className = 'document-item';
                listItem.innerHTML = `
                    <a href="/documents/${doc.id}/versions/1/download" target="_blank">${doc.title}</a>
                    - ${doc.description || 'No Description'}
                    <button onclick="showVersions(${doc.id}, '${doc.title}')">View Versions</button>
                `;
                documentsList.appendChild(listItem);
            });
        }
    } catch (error) {
        console.error('Error fetching documents:', error);
        messageDiv.className = 'error';
        messageDiv.textContent = error.message.includes('500')
            ? 'Server error. Please try again later.'
            : `Error: ${error.message}`;
        documentsList.innerHTML = 'Failed to load documents.';
    }
}

async function showSearch(event) {
    if (event) event.preventDefault();
    homeContent.style.display = 'none';
    uploadContent.style.display = 'none';
    documentsContent.style.display = 'none';
    searchContent.style.display = 'block';
    messageDiv.textContent = '';

    const searchResultsList = document.getElementById('search-results').querySelector('ul');
    searchResultsList.innerHTML = '';

    const query = document.getElementById('search-query').value;
    if (!query.trim()) return;

    try {
        const response = await fetchWithAuth(`http://127.0.0.1:8000/documents/search/?query=${encodeURIComponent(query)}`, {
            method: 'GET'
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Search failed: ${response.status} ${response.statusText} - ${errorText}`);
        }
        const data = await response.json();
        console.log('Search response:', data);

        if (!data || !Array.isArray(data.results)) {
            throw new Error('Expected an array of search results, but received: ' + JSON.stringify(data));
        }

        searchResultsList.innerHTML = '';
        if (data.results.length === 0) {
            searchResultsList.innerHTML = `No matching documents found for "${query}".`;
        } else {
            data.results.forEach(doc => {
                if (!doc || typeof doc !== 'object' || !doc.title || !doc.id) {
                    console.warn('Invalid document object:', doc);
                    return;
                }
                const listItem = document.createElement('li');
                listItem.className = 'document-item';
                listItem.innerHTML = `
                    <a href="/documents/${doc.id}/versions/1/download" target="_blank">${doc.title}</a>
                    - ${doc.description || 'No Description'}
                    <button onclick="showVersions(${doc.id}, '${doc.title}')">View Versions</button>
                `;
                searchResultsList.appendChild(listItem);
            });
        }
    } catch (error) {
        console.error('Error searching documents:', error);
        messageDiv.className = 'error';
        messageDiv.textContent = error.message.includes('500')
            ? 'Server error. Please try again later.'
            : `Error: ${error.message}`;
        searchResultsList.innerHTML = 'Search failed.';
    }
}

async function showVersions(documentId, documentTitle) {
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

        if (!data || !Array.isArray(data.versions)) {
            throw new Error('Expected an array of versions, but received: ' + JSON.stringify(data));
        }

        versionsList.innerHTML = `<h4>Versions for ${documentTitle}</h4>`;
        if (data.versions.length === 0) {
            versionsList.innerHTML += '<li>No versions found.</li>';
        } else {
            data.versions.forEach(version => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `
                    Version ${version.version} (Uploaded: ${new Date(version.uploaded_at).toLocaleString()})
                    <a href="/documents/${documentId}/versions/${version.version}/download" target="_blank">Download</a>
                `;
                versionsList.appendChild(listItem);
            });
        }
        versionsModal.style.display = 'block';
    } catch (error) {
        console.error('Error fetching versions:', error);
        messageDiv.className = 'error';
        messageDiv.textContent = `Error fetching versions: ${error.message}`;
    }
}

homeLink.addEventListener('click', showHome);
uploadLink.addEventListener('click', showUpload);
documentsLink.addEventListener('click', showDocuments);
searchLink.addEventListener('click', showSearch);
document.getElementById('search-form').addEventListener('submit', showSearch);

logoutLink.addEventListener('click', () => {
    localStorage.removeItem('accessToken');
    window.location.href = '/';
});

document.getElementById('uploadForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const description = document.getElementById('description').value;
    const fileInput = document.getElementById('file');
    const messageDiv = document.getElementById('upload-message');

    if (fileInput.files.length === 0) {
        messageDiv.className = 'error';
        messageDiv.textContent = 'Please select a file to upload.';
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        messageDiv.className = 'error';
        messageDiv.textContent = 'Please upload a PDF file.';
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        messageDiv.className = 'error';
        messageDiv.textContent = 'File size exceeds 10MB.';
        return;
    }

    const formData = new FormData();
    formData.append('description', description);
    formData.append('file', file);

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
        messageDiv.className = 'success';
        messageDiv.textContent = data.message;
        document.getElementById('description').value = '';
        document.getElementById('file').value = '';
        await showDocuments();
    } catch (error) {
        messageDiv.className = 'error';
        messageDiv.textContent = `Error: ${error.message}`;
    }
});

async function checkToken() {
    try {
        const response = await fetch('http://127.0.0.1:8000/users/me', {
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'accept': 'application/json'
            }
        });
        if (!response.ok) {
            console.error(`Token validation failed: ${response.status} ${response.statusText}`);
            localStorage.removeItem('accessToken');
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Error checking token:', error);
        localStorage.removeItem('accessToken');
        window.location.href = '/';
    }
}

// Modal close handler
closeModal.addEventListener('click', () => {
    versionsModal.style.display = 'none';
});

// Close modal when clicking outside
window.addEventListener('click', (event) => {
    if (event.target === versionsModal) {
        versionsModal.style.display = 'none';
    }
});

// Enable/disable search button
document.getElementById('search-query').addEventListener('input', (e) => {
    document.getElementById('search-button').disabled = !e.target.value.trim();
});

// Initialize
checkToken();
fetchUserDetails();
showHome();