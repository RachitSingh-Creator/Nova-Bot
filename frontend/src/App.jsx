import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Chat from "./pages/Chat";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import { getAccessToken } from "./services/api";

function PrivateRoute({ children }) {
  if (!getAccessToken()) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Chat />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
