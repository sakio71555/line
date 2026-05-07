import { useEffect, useMemo, useState } from "react";

import { AppHeader } from "./components/AppHeader";
import { getMissingFrontendEnv } from "./lib/env";
import { useLiffProfile } from "./hooks/useLiffProfile";
import { AdminJobsPage } from "./pages/AdminJobsPage";
import { CompanySearchPage } from "./pages/CompanySearchPage";
import { JobSubmissionPage } from "./pages/JobSubmissionPage";
import { JobListPage } from "./pages/JobListPage";
import { VehicleAvailabilityPage } from "./pages/VehicleAvailabilityPage";
import type { JobFilters } from "./types/job";

const initialFilters: JobFilters = {
  pickup: "",
  delivery: "",
  vehicleType: "",
  status: "",
  reviewOnly: false,
};

type Tab = "jobs" | "submit" | "vehicle" | "admin" | "companies";
type ListView = "jobs" | "vehicles";

const queryTabMap: Record<string, Tab> = {
  list: "jobs",
  post: "submit",
  vehicle: "vehicle",
  admin: "admin",
  companies: "companies",
  company: "companies",
};

function getInitialTab(): Tab {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  if (tab === "vehicles" || tab === "vehicle_availabilities") return "jobs";
  return tab ? queryTabMap[tab] ?? "jobs" : "jobs";
}

function getInitialListView(): ListView {
  const params = new URLSearchParams(window.location.search);
  const tab = params.get("tab");
  return tab === "vehicles" || tab === "vehicle_availabilities" ? "vehicles" : "jobs";
}

function getInitialSessionId(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get("session_id");
}

function App() {
  const profile = useLiffProfile();
  const [activeTab, setActiveTab] = useState<Tab>(getInitialTab);
  const [listView, setListView] = useState<ListView>(getInitialListView);
  const [filters, setFilters] = useState<JobFilters>(initialFilters);
  const [sessionId] = useState<string | null>(getInitialSessionId);
  const missingEnv = useMemo(() => getMissingFrontendEnv(), []);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [activeTab]);

  return (
    <div className="app">
      <AppHeader profile={profile} />

      {missingEnv.length > 0 ? (
        <section className="notice notice-warning">
          <strong>フロントエンド環境変数が不足しています。</strong>
          <span>{missingEnv.join(", ")}</span>
        </section>
      ) : null}

      {profile.error ? (
        <section className="notice">
          <strong>LIFF初期化はスキップされました。</strong>
          <span>ブラウザでの開発確認は続行できます。</span>
        </section>
      ) : null}

      <nav className="tabbar" aria-label="画面切り替え">
        <button
          type="button"
          className={activeTab === "jobs" ? "active" : ""}
          onClick={() => {
            setActiveTab("jobs");
            setListView("jobs");
          }}
        >
          案件一覧
        </button>
        <button
          type="button"
          className={activeTab === "submit" ? "active" : ""}
          onClick={() => setActiveTab("submit")}
        >
          案件投稿
        </button>
        <button
          type="button"
          className={activeTab === "vehicle" ? "active" : ""}
          onClick={() => setActiveTab("vehicle")}
        >
          空車登録
        </button>
        <button
          type="button"
          className={activeTab === "admin" ? "active" : ""}
          onClick={() => setActiveTab("admin")}
        >
          管理
        </button>
        <button
          type="button"
          className={activeTab === "companies" ? "active" : ""}
          onClick={() => setActiveTab("companies")}
        >
          企業検索
        </button>
      </nav>

      {activeTab === "jobs" ? (
        <JobListPage
          filters={filters}
          onFiltersChange={setFilters}
          listView={listView}
          onListViewChange={setListView}
        />
      ) : null}
      {activeTab === "submit" ? (
        <JobSubmissionPage
          profile={profile}
          sessionId={sessionId}
          onNavigateToJobs={() => setActiveTab("jobs")}
        />
      ) : null}
      {activeTab === "vehicle" ? <VehicleAvailabilityPage profile={profile} /> : null}
      {activeTab === "admin" ? (
        <AdminJobsPage filters={filters} profile={profile} />
      ) : null}
      {activeTab === "companies" ? <CompanySearchPage /> : null}
    </div>
  );
}

export default App;
