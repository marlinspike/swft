import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@components/AppShell";
import { DashboardPage } from "@pages/Dashboard";
import { ProjectPage } from "@pages/ProjectView";
import { RunPage } from "@pages/RunView";

export const App = () => (
  <BrowserRouter>
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/runs/:runId" element={<RunPage />} />
      </Routes>
    </AppShell>
  </BrowserRouter>
);
