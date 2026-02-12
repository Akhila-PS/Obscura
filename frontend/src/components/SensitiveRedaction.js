// src/components/SensitiveRedaction.js
import React, { useState } from "react";
import {
  Container,
  Typography,
  Box,
  IconButton,
  CircularProgress,
  Alert,
  Divider,
  Tooltip,
  FormControlLabel,
  Checkbox,
  Paper,
  Button,
} from "@mui/material";
import { motion } from "framer-motion";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";

import UploadSection from "../feature/UploadSection";
import ResultsSection from "../feature/ResultsSection";
import axios from "axios";

function SensitiveRedaction({ mode, toggleColorMode }) {
  const navigate = useNavigate();
  
  const [originalFile, setOriginalFile] = useState(null);
  const [redactedOutput, setRedactedOutput] = useState(null);
  const [outputType, setOutputType] = useState(null);
  const [riskScore, setRiskScore] = useState(null);
  const [explanations, setExplanations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [redactionOptions, setRedactionOptions] = useState({
    aadhaar: true,
    vid: true,
    phone: true,
    qr: true,
    face: false,
    email: false,
    plate: false,
    partial: true,
    watermark: true,
  });

  const handleOptionChange = (key) => {
    setRedactionOptions((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleUpload = async (file) => {
    if (!file) {
      setError("No file selected.");
      return;
    }

    setLoading(true);
    setError(null);
    setOriginalFile(URL.createObjectURL(file));

    const formData = new FormData();
    formData.append("image", file);
    formData.append("options", JSON.stringify(redactionOptions));

    try {
      const res = await axios.post("http://localhost:5000/upload", formData, {
        timeout: 120000,
      });

      setOutputType(res.data.type);
      setRiskScore(res.data.risk_score);
      setExplanations(res.data.explanations || []);

      if (res.data.type === "image") {
        setRedactedOutput(`data:image/png;base64,${res.data.redacted_image}`);
      }

      if (res.data.type === "pdf") {
        const binary = atob(res.data.redacted_pdf);
        const bytes = new Uint8Array([...binary].map((c) => c.charCodeAt(0)));
        const blob = new Blob([bytes], { type: "application/pdf" });
        setRedactedOutput(URL.createObjectURL(blob));
      }
    } catch (err) {
      console.error("Upload error:", err);
      const errorMessage =
        err?.response?.data?.error ||
        err?.message ||
        "Failed to process file. Please try again.";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: { xs: 4, md: 8 }, position: 'relative' }}>
      {/* Back Button */}
      <IconButton
        onClick={() => navigate("/")}
        sx={{
          position: 'absolute',
          top: 24,
          left: 24,
          color: 'text.secondary',
          '&:hover': { color: 'primary.main' },
        }}
      >
        <ArrowBackIcon />
      </IconButton>

      {/* Theme Toggle */}
      <Tooltip title={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}>
        <IconButton
          onClick={toggleColorMode}
          sx={{
            position: 'absolute',
            top: 24,
            right: 24,
            color: 'text.secondary',
            '&:hover': { color: 'primary.main' },
          }}
        >
          {mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>
      </Tooltip>

      {/* Hero Title */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
      >
        <Typography
          variant="h3"
          align="center"
          sx={{
            fontWeight: 900,
            background: 'linear-gradient(90deg, #60A5FA 0%, #3B82F6 50%, #2563EB 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            mb: 2,
            textShadow: '0 6px 24px rgba(59,130,246,0.3)',
          }}
        >
          Sensitive Information Redaction
        </Typography>

        <Typography
          variant="subtitle1"
          align="center"
          color="text.secondary"
          sx={{ mb: 6, fontSize: '1.1rem' }}
        >
          Auto-detect & obscure Aadhaar, phones, emails, QR codes & more
        </Typography>
      </motion.div>

      {/* Redaction Options */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
      >
        <Paper
          elevation={6}
          sx={{
            p: 4,
            mb: 4,
            borderRadius: 4,
            background: mode === 'dark' 
              ? 'linear-gradient(145deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.98) 100%)'
              : 'rgba(255,255,255,0.95)',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
            🎯 Customize Redaction Options
          </Typography>

          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.aadhaar}
                  onChange={() => handleOptionChange('aadhaar')}
                  color="primary"
                />
              }
              label="Aadhaar Numbers"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.vid}
                  onChange={() => handleOptionChange('vid')}
                  color="primary"
                />
              }
              label="VID Numbers (16 digits)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.phone}
                  onChange={() => handleOptionChange('phone')}
                  color="primary"
                />
              }
              label="Phone Numbers"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.qr}
                  onChange={() => handleOptionChange('qr')}
                  color="primary"
                />
              }
              label="QR Codes"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.face}
                  onChange={() => handleOptionChange('face')}
                  color="secondary"
                />
              }
              label="Faces (Blur)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.email}
                  onChange={() => handleOptionChange('email')}
                  color="secondary"
                />
              }
              label="Email Addresses"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.plate}
                  onChange={() => handleOptionChange('plate')}
                  color="secondary"
                />
              }
              label="License Plates"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.partial}
                  onChange={() => handleOptionChange('partial')}
                  color="primary"
                />
              }
              label="Partial Redaction (show last 4)"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={redactionOptions.watermark}
                  onChange={() => handleOptionChange('watermark')}
                  color="primary"
                />
              }
              label="Add Watermark"
            />
          </Box>
        </Paper>
      </motion.div>

      {/* Upload Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <Box
          sx={{
            bgcolor: 'background.paper',
            borderRadius: 4,
            p: { xs: 4, md: 5 },
            boxShadow: mode === 'dark' 
              ? '0 15px 35px rgba(0,0,0,0.5)' 
              : '0 15px 35px rgba(0,0,0,0.1)',
            border: '1px solid',
            borderColor: 'divider',
            textAlign: 'center',
            maxWidth: '480px',
            mx: 'auto',
          }}
        >
          <CloudUploadIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />

          <UploadSection onUpload={handleUpload} />

          {loading && (
            <Box mt={4}>
              <CircularProgress size={50} thickness={5} />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Processing your file...
              </Typography>
            </Box>
          )}
        </Box>
      </motion.div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Alert severity="error" sx={{ mt: 4, borderRadius: 3 }}>
            {error}
          </Alert>
        </motion.div>
      )}

      {redactedOutput && (
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}
        >
          <Divider sx={{ my: 8, borderColor: 'divider' }} />

          <ResultsSection
            originalFile={originalFile}
            redactedOutput={redactedOutput}
            outputType={outputType}
            riskScore={riskScore}
            explanations={explanations}
          />
        </motion.div>
      )}
    </Container>
  );
}

export default SensitiveRedaction;