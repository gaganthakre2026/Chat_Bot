import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { uploadDocument } from "../api/client.js";

export default function UploadButton({ token, onUploaded, disabled }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setProgress(0);

    try {
      const response = await uploadDocument(file, token, setProgress);
      onUploaded(response.document);
    } catch (uploadError) {
      alert(uploadError.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        className="hidden"
        type="file"
        accept="application/pdf,.pdf"
        onChange={handleFileChange}
      />
      <button
        type="button"
        disabled={disabled || uploading}
        onClick={() => inputRef.current?.click()}
        className="inline-flex h-10 items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 text-sm font-semibold text-white shadow-md shadow-indigo-200 transition hover:from-indigo-500 hover:to-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
        title="Upload PDF"
      >
        <UploadCloud size={18} />
        {uploading ? `Uploading ${progress}%` : "Upload PDF"}
      </button>
    </>
  );
}
