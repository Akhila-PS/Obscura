// src/components/LandingPage.js
import React from "react";
import { Box, Typography, Button, Container, Paper } from "@mui/material";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import SecurityIcon from "@mui/icons-material/Security";
import PrivacyTipIcon from "@mui/icons-material/PrivacyTip";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 12, md: 16 }, position: "relative" }}>
      {/* Subtle background depth */}
     

      {/* Single Hero Title – Exact same gradient as Sensitive page */}
      <motion.div
        initial={{ opacity: 0, y: -60 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.1, ease: "easeOut" }}
      >
        <Typography
          variant="h1"
          align="center"
          sx={{
            fontSize: { xs: "3.8rem", md: "6.2rem" },
            fontWeight: 900,
            letterSpacing: "-0.04em",
            background: "linear-gradient(90deg, #60A5FA 0%, #3B82F6 50%, #2563EB 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            mb: 1,
            textShadow: "0 8px 32px rgba(59,130,246,0.4)",
          }}
        >
          Obscura
        </Typography>

        <Typography
          variant="h5"
          align="center"
          color="text.secondary"
          sx={{
            fontWeight: 400,
            maxWidth: 720,
            mx: "auto",
            mb: 10,
            lineHeight: 1.5,
            opacity: 0.92,
          }}
        >
          Privacy by Design • Invisible • Secure • Effortless
        </Typography>
      </motion.div>

      {/* Uniform Cards */}
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          justifyContent: "center",
          alignItems: "stretch",
          gap: { xs: 6, md: 8 },
        }}
      >
        {/* Metadata Card */}
        <motion.div
          whileHover={{ scale: 1.05, y: -12 }}
          whileTap={{ scale: 0.98 }}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <Paper
            elevation={12}
            sx={{
            width: { xs: "100%", md: 400 },
            p: { xs: 5, md: 6 },
            borderRadius: 5,
            background: "linear-gradient(145deg, rgba(30,41,59,0.94) 0%, rgba(15,23,42,0.98) 100%)",
            border: "1px solid rgba(96,165,250,0.22)",
            backdropFilter: "blur(14px)",
            textAlign: "center",

            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",

          height: "100%",        // ✅ add
           minHeight: 520,        // ✅ add (makes both equal)

          transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
          "&:hover": {
         borderColor: "#60A5FA",
         boxShadow: "0 25px 50px rgba(59,130,246,0.35)",
  },
}}

            onClick={() => navigate("/metadata-redaction")}
          >
            <PrivacyTipIcon sx={{ fontSize: 80, color: "#60A5FA", mb: 4, mx: "auto" }} />
            <Box>
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, mb: 2 }}>
                Metadata Redaction
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 5, lineHeight: 1.7 }}>
                Remove hidden EXIF, GPS, camera info, timestamps, and location data from images.
              </Typography>
            </Box>
            <Button
              variant="contained"
              fullWidth
              sx={{
                py: 2,
                fontSize: "1.1rem",
                background: "linear-gradient(90deg, #3B82F6, #2563EB)",
                "&:hover": { background: "linear-gradient(90deg, #60A5FA, #3B82F6)" },
              }}
            >
              Start Metadata Cleanup
            </Button>
          </Paper>
        </motion.div>

        {/* Sensitive Information Card */}
        <motion.div
          whileHover={{ scale: 1.05, y: -12 }}
          whileTap={{ scale: 0.98 }}
          transition={{ type: "spring", stiffness: 300 }}
        >
          <Paper
            elevation={12}
            sx={{
  width: { xs: "100%", md: 400 },
  p: { xs: 5, md: 6 },
  borderRadius: 5,
  background: "linear-gradient(145deg, rgba(30,41,59,0.94) 0%, rgba(15,23,42,0.98) 100%)",
  border: "1px solid rgba(96,165,250,0.22)",
  backdropFilter: "blur(14px)",
  textAlign: "center",

  display: "flex",
  flexDirection: "column",
  justifyContent: "space-between",

  height: "100%",        // ✅ add
  minHeight: 520,        // ✅ add (makes both equal)

  transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
  "&:hover": {
    borderColor: "#60A5FA",
    boxShadow: "0 25px 50px rgba(59,130,246,0.35)",
  },
}}

            onClick={() => navigate("/sensitive-redaction")}
          >
            <SecurityIcon sx={{ fontSize: 80, color: "#60A5FA", mb: 4, mx: "auto" }} />
            <Box>
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 700, mb: 2 }}>
                Sensitive Information Redaction
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 5, lineHeight: 1.7 }}>
                Auto-detect & permanently obscure Aadhaar, phones, emails, names, cards, QR codes & more.
              </Typography>
            </Box>
            <Button
              variant="contained"
              fullWidth
              sx={{
                py: 2,
                fontSize: "1.1rem",
                background: "linear-gradient(90deg, #3B82F6, #2563EB)",
                "&:hover": { background: "linear-gradient(90deg, #60A5FA, #3B82F6)" },
              }}
            >
              Start Sensitive Redaction
            </Button>
          </Paper>
        </motion.div>
      </Box>

      {/* Footer tagline */}
      <Typography
  variant="h1"
  align="center"
  sx={{
    fontSize: { xs: "3.8rem", md: "6.2rem" },
    fontWeight: 900,
    letterSpacing: "-0.04em",
    background: "linear-gradient(90deg, #60A5FA 0%, #3B82F6 50%, #2563EB 100%) !important",
    WebkitBackgroundClip: "text !important",
    WebkitTextFillColor: "transparent !important",
    mb: 1,
    textShadow: "0 8px 32px rgba(59,130,246,0.4) !important",
  }}
>
</Typography>
    </Container>
  );
}