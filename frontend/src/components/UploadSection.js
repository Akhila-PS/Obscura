// src/components/UploadSection.js
import { Box, Button, Typography } from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { useState } from "react";

export default function UploadSection({ onUpload }) {
  const [isDragOver, setIsDragOver] = useState(false);

const handleDragOver = (e) => {
  e.preventDefault();
  setIsDragOver(true);
};

const handleDragLeave = () => {
  setIsDragOver(false);
};

const handleDrop = (e) => {
  e.preventDefault();
  setIsDragOver(false);
  const file = e.dataTransfer.files[0];
  if (file) {
    onUpload(file);
  }
};
  return (
    <Box sx={{ mt: 2 }}>
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
          borderColor: 'primary.main',
          color: 'primary.main',
          px: 6,
          py: 3,
          fontSize: '1.1rem',
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
          accept="image/*,application/pdf"
          onChange={(e) => onUpload(e.target.files[0])}
        />
      </Button>
    </Box>
  );
}