import "./App.css";
import { Container } from "@mui/material";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import io from "socket.io-client";
import ThemeProvider from "./ThemeProvider";
import NavBar from "./components/NavBar";
import Simulation from "./components/simulator/Simulation";
import Resource from "./components/resource/Resource";

export const socket = io.connect("http://localhost:5000/");

function App(props) {
  const { colorMode } = props;

  return (
    <ThemeProvider mode={colorMode}>
      <NavBar></NavBar>
      <Container maxWidth="xl">
        <BrowserRouter>
          <Routes>
            <Route path="/simulator" element={<Simulation />} />
            <Route path="/resources" element={<Resource />} />
            <Route path="*" element={<Navigate replace to="/simulator" />} />
          </Routes>
        </BrowserRouter>
      </Container>
    </ThemeProvider>
  );
}

export default App;
