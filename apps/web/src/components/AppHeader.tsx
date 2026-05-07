import type { LiffProfileState } from "../lib/liff";

type Props = {
  profile: LiffProfileState;
};

export function AppHeader({ profile }: Props) {
  const profileLabel = profile.displayName
    ? `${profile.displayName} さん`
    : profile.error
      ? "開発確認モード"
      : "LINEプロフィール未取得";

  return (
    <header className="app-header">
      <div>
        <p className="app-header__eyebrow">LINE Transport Matching</p>
        <h1>運送案件</h1>
      </div>
      <div className="profile-chip">
        <span>{profile.inClient ? "LINE内" : "ブラウザ"}</span>
        <strong>{profileLabel}</strong>
      </div>
    </header>
  );
}
