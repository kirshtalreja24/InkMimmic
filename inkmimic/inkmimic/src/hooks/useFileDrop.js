import { useCallback, useState } from 'react';

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'application/pdf'];

/**
 * Drag-and-drop + click-to-browse file intake. Returns everything a drop
 * zone component needs: current file, drag state, and the handlers to spread
 * onto the container.
 */
export function useFileDrop({ onFile } = {}) {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);

  const acceptFile = useCallback(
    (candidate) => {
      if (!candidate) return;
      if (!ACCEPTED_TYPES.includes(candidate.type)) {
        setError('Use a PNG, JPG, WEBP, or PDF of your handwriting.');
        return;
      }
      setError(null);
      setFile(candidate);
      onFile?.(candidate);
    },
    [onFile]
  );

  const handlers = {
    onDragOver: (e) => {
      e.preventDefault();
      setIsDragging(true);
    },
    onDragLeave: (e) => {
      e.preventDefault();
      setIsDragging(false);
    },
    onDrop: (e) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = e.dataTransfer.files?.[0];
      acceptFile(dropped);
    },
  };

  const onBrowse = (e) => {
    const picked = e.target.files?.[0];
    acceptFile(picked);
  };

  const reset = () => {
    setFile(null);
    setError(null);
  };

  return { file, isDragging, error, handlers, onBrowse, reset };
}
