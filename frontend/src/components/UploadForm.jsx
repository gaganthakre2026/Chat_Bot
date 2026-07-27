import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { uploadDocument } from "../api/client.js";

export default function UploadForm({ token, onUploaded }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setError("");

    try {
      const response = await uploadDocument(file, token, setProgress);
      onUploaded(response.document);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <section className="border-b border-slate-200 p-4">
      <input
        ref={inputRef}
        className="hidden"
        type="file"
        accept="application/pdf,.pdf"
        onChange={handleFileChange}
      />
      <button
        type="button"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
        className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-teal-700 px-3 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60"
        title="Upload PDF"
      >
        <UploadCloud size={18} />
        {uploading ? "Uploading..." : "Upload PDF"}
      </button>

      {uploading ? (
        <div className="mt-3 h-2 overflow-hidden rounded-md bg-slate-200">
          <div className="h-full bg-teal-600 transition-all" style={{ width: `${progress}%` }} />
        </div>
      ) : null}

      {error ? <p className="mt-3 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p> : null}
    </section>
  );
}
