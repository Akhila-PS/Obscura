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
} from "@mui/material";
import { motion } from "framer-motion";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";

import UploadSection from "./components/UploadSection";
import ResultsSection from "./components/ResultsSection";
import axios from "axios";
import { useColorMode } from "./index";

import "./App.css";

function App() {
  const { toggleColorMode } = useColorMode();
  const [mode, setMode] = useState('dark'); // local state to sync icon
  const [originalFile, setOriginalFile] = useState(null);
  const [redactedOutput, setRedactedOutput] = useState(null);
  const [outputType, setOutputType] = useState(null);
  const [riskScore, setRiskScore] = useState(null);
  const [explanations, setExplanations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleToggle = () => {
    toggleColorMode();
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
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

    try {
      // Let axios set the correct multipart boundary automatically.
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
      console.error("Upload error:", {
        message: err?.message,
        code: err?.code,
        status: err?.response?.status,
        data: err?.response?.data,
      });
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
      {/* Theme Toggle - Top Right */}
      <Tooltip title={`Switch to ${mode === 'dark' ? 'light' : 'dark'} mode`}>
        <IconButton
          onClick={handleToggle}
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
          variant="h2"
          component="h1"
          align="center"
          sx={{
            background: 'linear-gradient(90deg, #60A5FA, #3B82F6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 800,
            letterSpacing: '-1px',
            mb: 1,
          }}
        >
          Obscura
        </Typography>

        <Typography
          variant="subtitle1"
          align="center"
          color="text.secondary"
          sx={{ mb: 6, fontSize: '1.1rem' }}
        >
          Privacy by Design • Secure • Automatic • Invisible
        </Typography>
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
    p: { xs: 4, md: 5 },          // ← Reduced padding (was 5/7)
    boxShadow: mode === 'dark' ? '0 15px 35px rgba(0,0,0,0.5)' : '0 15px 35px rgba(0,0,0,0.1)',
    border: '1px solid',
    borderColor: 'divider',
    textAlign: 'center',
    maxWidth: '480px',            // ← NEW: limits width (was full container)
    mx: 'auto',                   // ← centers it
  }}
>
  <CloudUploadIcon sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />  {/* smaller icon */}

  <UploadSection onUpload={handleUpload} />

  {loading && (
    <Box mt={4}>
      <CircularProgress size={50} thickness={5} />
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

export default App;