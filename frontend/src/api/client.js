// In dev, use same-origin requests so Vite proxies to the backend (see vite.config.cjs).
// In production, set VITE_API_BASE_URL to your deployed backend URL.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "" : "http://localhost:8000");

function networkError() {
  return new Error(
    "Cannot reach the backend API. Make sure the backend is running on http://localhost:8000, then refresh this page.",
  );
}

async function parseResponse(response) {
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      throw new Error(`Unexpected server response (${response.status}).`);
    }
  }
  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join(", ")
          : `Request failed with status ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

export async function apiRequest(path, token, options = {}) {
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw networkError();
  }
  return parseResponse(response);
}

export function uploadDocument(file, token, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);

    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/documents/upload`);
    request.setRequestHeader("Authorization", `Bearer ${token}`);

    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    request.onload = () => {
      try {
        const payload = request.responseText ? JSON.parse(request.responseText) : null;
        if (request.status >= 200 && request.status < 300) {
          resolve(payload);
        } else {
          const detail = payload?.detail;
          reject(
            new Error(
              typeof detail === "string" ? detail : `Upload failed with status ${request.status}`,
            ),
          );
        }
      } catch (error) {
        reject(error);
      }
    };
    request.onerror = () => reject(networkError());
    request.send(formData);
  });
}

export function listDocuments(token) {
  return apiRequest("/documents", token);
}

export function getDocument(documentId, token) {
  return apiRequest(`/documents/${documentId}`, token);
}

export function deleteDocument(documentId, token) {
  return apiRequest(`/documents/${documentId}`, token, { method: "DELETE" });
}

export function sendMessage(documentId, question, sessionId, token) {
  const body = { question };
  if (sessionId) {
    body.session_id = sessionId;
  }
  return apiRequest(`/chat/${documentId}/message`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getHistory(sessionId, token) {
  return apiRequest(`/chat/${sessionId}/history`, token);
}

export function signUp(email, password) {
  return apiRequest("/auth/sign-up", null, {
    method: "POST",
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
}

export function signIn(email, password) {
  return apiRequest("/auth/sign-in", null, {
    method: "POST",
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
}

export function logout(token) {
  return apiRequest("/auth/logout", token, { method: "POST" });
}

export { API_BASE_URL };
