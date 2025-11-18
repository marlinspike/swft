import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@components/AppShell";
import { DashboardPage } from "@pages/Dashboard";
import { ProjectPage } from "@pages/ProjectView";
import { RunPage } from "@pages/RunView";
import { SwftHomePage } from "@pages/SwftHome";
import { SwftWorkspacePage } from "@pages/SwftWorkspace";
import { SWFT_WORKSPACE_ENABLED } from "@lib/features";

export const App = () => (
  <BrowserRouter future={{ v7_relativeSplatPath: true }}>
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/runs/:runId" element={<RunPage />} />
        {SWFT_WORKSPACE_ENABLED ? (
          <>
            <Route path="/swft" element={<SwftHomePage />} />
            <Route path="/swft/:projectId" element={<SwftWorkspacePage />} />
          </>
        ) : (
          <>
            <Route path="/swft" element={<Navigate to="/" replace />} />
            <Route path="/swft/:projectId" element={<Navigate to="/" replace />} />
          </>
        )}
      </Routes>
    </AppShell>
  </BrowserRouter>
);
