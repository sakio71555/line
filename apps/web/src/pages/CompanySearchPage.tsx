import { FormEvent, useState } from "react";

import { searchCompanies, type CompanySearchItem } from "../lib/liffApi";

export function CompanySearchPage() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<CompanySearchItem[]>([]);
  const [count, setCount] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  async function handleSearch(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmedQuery = query.trim();
    setError(null);
    setMessage(null);
    setHasSearched(true);

    if (!trimmedQuery) {
      setItems([]);
      setCount(0);
      setOpenIndex(null);
      setMessage("検索語を入力してください。");
      return;
    }

    setIsLoading(true);
    try {
      const result = await searchCompanies(trimmedQuery, 50);
      setItems(result.items);
      setCount(result.count);
      setOpenIndex(null);
      setMessage(result.message ?? null);
    } catch (searchError) {
      setItems([]);
      setCount(0);
      setOpenIndex(null);
      setError(searchError instanceof Error ? searchError.message : "企業検索APIに接続できませんでした。");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="form-panel company-search-panel">
        <div className="form-panel__header">
          <div>
            <h2>企業検索</h2>
            <p>会社名、氏名、電話番号、メール、住所などで検索できます。</p>
          </div>
        </div>

        <form className="company-search-form" onSubmit={handleSearch}>
          <label>
            <span>検索語</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="会社名・氏名・電話番号など"
              inputMode="search"
            />
          </label>
          <button type="submit" className="form-submit primary-action" disabled={isLoading}>
            {isLoading ? "検索中..." : "検索"}
          </button>
        </form>
      </section>

      {error ? (
        <section className="notice notice-error">
          <strong>企業検索APIに接続できませんでした</strong>
          <span>{error}</span>
        </section>
      ) : null}

      {message ? (
        <section className="notice">
          <span>{message}</span>
        </section>
      ) : null}

      {hasSearched && !isLoading && !error ? (
        <section className="list-summary">
          <span>検索結果</span>
          <strong>{count}件</strong>
        </section>
      ) : null}

      {isLoading ? <p className="empty-state">検索中...</p> : null}

      {hasSearched && !isLoading && !error && items.length === 0 && !message ? (
        <p className="empty-state">該当する企業が見つかりませんでした</p>
      ) : null}

      <div className="company-list">
        {items.map((item, index) => (
          <CompanyCard
            key={`${item.company}-${item.name}-${item.mobile}-${index}`}
            item={item}
            isOpen={openIndex === index}
            onToggle={() => setOpenIndex((current) => (current === index ? null : index))}
          />
        ))}
      </div>
    </main>
  );
}

function CompanyCard({
  item,
  isOpen,
  onToggle,
}: {
  item: CompanySearchItem;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <article className={isOpen ? "company-card company-card--open" : "company-card"}>
      <button
        type="button"
        className="company-card__summary-button"
        aria-expanded={isOpen}
        onClick={onToggle}
      >
        <span className="company-card__company">{displayValue(item.company, "会社名未入力")}</span>
        {companySummary(item) ? <span className="company-card__summary">{companySummary(item)}</span> : null}
      </button>

      {isOpen ? (
        <dl className="company-card__grid">
          <CompanyField label="会社名" value={item.company} required />
          <CompanyField label="役職" value={item.title} />
          <CompanyField label="氏名" value={item.name} required />
          <CompanyField label="ローマ字" value={item.name_roman} />
          <CompanyField label="TEL" value={item.tel} href={phoneHref(item.tel)} />
          <CompanyField label="携帯" value={item.mobile} href={phoneHref(item.mobile)} />
          <CompanyField label="FAX" value={item.fax} />
          <CompanyField label="フリーダイヤル" value={item.toll_free} href={phoneHref(item.toll_free)} />
          <CompanyField label="メール" value={item.email} href={mailHref(item.email)} />
          <CompanyField label="郵便番号" value={item.postal} />
          <CompanyField label="地域" value={item.region} />
          <CompanyField label="住所" value={joinAddress(item.address1, item.address3)} wide />
          <CompanyField label="支店" value={item.branches} wide />
          <CompanyField label="URL" value={item.url} href={externalHref(item.url)} external wide />
          <CompanyField label="LINE URL" value={item.line_url} href={externalHref(item.line_url)} external wide />
          <CompanyField label="Notes" value={item.notes} wide />
        </dl>
      ) : null}

      <button type="button" className="company-card__toggle" onClick={onToggle}>
        {isOpen ? "閉じる" : "詳細を見る"}
      </button>
    </article>
  );
}

function CompanyField({
  label,
  value,
  href,
  external = false,
  wide = false,
  required = false,
}: {
  label: string;
  value: string;
  href?: string | null;
  external?: boolean;
  wide?: boolean;
  required?: boolean;
}) {
  const display = displayValue(value);
  if (!required && !value.trim()) return null;
  return (
    <div className={wide ? "company-field company-field--wide" : "company-field"}>
      <dt>{label}</dt>
      <dd>
        {href && value.trim() ? (
          <a href={href} target={external ? "_blank" : undefined} rel={external ? "noreferrer" : undefined}>
            {display}
          </a>
        ) : (
          display
        )}
      </dd>
    </div>
  );
}

function displayValue(value: string, fallback = "未入力"): string {
  return value.trim() || fallback;
}

function companySummary(item: CompanySearchItem): string {
  return [item.region, item.name].filter((value) => value.trim()).join(" / ");
}

function phoneHref(value: string): string | null {
  const normalized = value.replace(/[^\d+]/g, "");
  return normalized ? `tel:${normalized}` : null;
}

function mailHref(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? `mailto:${trimmed}` : null;
}

function externalHref(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function joinAddress(address1: string, address3: string): string {
  return [address1, address3].filter((value) => value.trim()).join(" ");
}
