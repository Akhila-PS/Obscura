// src/components/UploadSection.js
import { Box, Button, Typography } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { useState } from "react";

export default function UploadSection({ onUpload }) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      validateAndUpload(file);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      validateAndUpload(file);
    }
  };

  const validateAndUpload = (file) => {
    const validTypes = ['image/', 'application/pdf'];
    const isValidType = validTypes.some(type => file.type.startsWith(type));
    
    if (!isValidType && !file.name.toLowerCase().endsWith('.pdf')) {
      // Fallback: check file extension if MIME type is not available
      const ext = file.name.toLowerCase().split('.').pop();
      const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'];
      if (!imageExts.includes(ext) && ext !== 'pdf') {
        alert('Please upload an image or PDF file.');
        return;
      }
    }
    
    onUpload(file);
  };

  return (
    <Box 
      sx={{ mt: 2 }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Drop your image or PDF here or click to upload
      </Typography>

      <Button
        variant="outlined"
        size="large"
        component="label"
        sx={{
          borderWidth: 2,
          borderStyle: 'dashed',
          borderColor: isDragOver ? 'primary.dark' : 'primary.main',
          backgroundColor: isDragOver ? 'action.hover' : 'transparent',
          color: 'primary.main',
          px: 6,
          py: 3,
          fontSize: '1.1rem',
          transition: 'all 0.2s ease',
          '&:hover': {
            bgcolor: 'primary.main',
            color: 'white',
            borderColor: 'primary.main',
          },
        }}
      >
        <CloudUploadIcon sx={{ mr: 2, fontSize: 32 }} />
        Choose File (Image / PDF)
        <input
          hidden
          type="file"
          accept="image/*,application/pdf,.pdf"
          onChange={handleFileSelect}
        />
      </Button>
    </Box>
  );
}