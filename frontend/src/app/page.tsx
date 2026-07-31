import Link from "next/link";
import { PriceChart } from "@/components/generative-ui/PriceChart";
import { FilingExcerpt } from "@/components/generative-ui/FilingExcerpt";

export default function Home() {
  return (
    <div className="min-h-screen bg-page font-body">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-12">
          <Link href="/" className="text-2xl font-semibold font-display text-accent tracking-tight">
            FinSight
          </Link>
          <div className="hidden md:flex gap-8 text-sm font-medium text-text-secondary">
            <Link href="/chat" className="hover:text-text-primary transition-colors">Agent</Link>
            <a href="#features" className="hover:text-text-primary transition-colors">Features</a>
            <a href="https://github.com" className="hover:text-text-primary transition-colors">GitHub</a>
          </div>
        </div>
        <Link href="/chat" className="btn-primary px-5 py-2.5 rounded-lg text-sm transition-all hover:shadow-md">
          Try the live demo
        </Link>
      </nav>

      {/* Hero Section */}
      <section className="px-8 pt-20 pb-32 max-w-[1400px] mx-auto">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          <div className="max-w-2xl">
            <p className="font-mono text-[11px] font-medium tracking-[0.25em] text-text-secondary uppercase mb-8">
              Live prices. Real filings. One agent.
            </p>
            <h1 className="font-display text-5xl md:text-7xl font-medium text-text-primary leading-[1.1] mb-8">
              Ask any market a question. <br />
              Get a cited answer back.
            </h1>
            <p className="text-lg text-text-secondary mb-10 max-w-lg leading-relaxed">
              A premium AI research assistant built for the US and Indian equity markets. Transparent, deterministic, and meticulously designed.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/chat" className="btn-primary px-8 py-3.5 rounded-lg text-sm transition-all hover:shadow-md text-center">
                Try the live demo
              </Link>
              <a href="https://github.com" className="btn-secondary px-8 py-3.5 rounded-lg text-sm transition-all text-center">
                View source on GitHub
              </a>
            </div>
          </div>
          
          {/* Floating Product Preview */}
          <div className="bg-panel border border-border rounded-2xl p-3 shadow-sm transform transition-transform hover:-translate-y-1 duration-300">
            <div className="px-4 pt-3 pb-2 flex items-center gap-2 border-b border-border mb-2">
              <div className="w-2.5 h-2.5 rounded-full bg-border-strong"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-border-strong"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-border-strong"></div>
            </div>
            <PriceChart 
              ticker="AAPL" 
              currency="USD"
              current_price={198.50} 
              period="1mo" 
              history={[
                { date: "2026-06-21", close: 192.30 },
                { date: "2026-06-28", close: 194.10 },
                { date: "2026-07-05", close: 196.50 },
                { date: "2026-07-12", close: 195.20 },
                { date: "2026-07-19", close: 198.50 },
              ]} 
            />
          </div>
        </div>
      </section>

      {/* Feature Section (Alternating) */}
      <section id="features" className="px-8 py-32 max-w-[1400px] mx-auto border-t border-border">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-32 items-center">
          {/* Visual Left */}
          <div className="order-2 lg:order-1 bg-panel border border-border rounded-3xl p-8 shadow-sm transform transition-transform hover:-translate-y-1 duration-300">
            <FilingExcerpt 
              documentTitle="Reliance Industries Annual Report 2024"
              ticker="RELIANCE.NS"
              source="seed"
              excerpts={[
                {
                  sectionTitle: "MANAGEMENT DISCUSSION AND ANALYSIS",
                  content: "The company's capital expenditure for FY2024 was ₹1,31,769 crore, primarily driven by the accelerated rollout of 5G networks and expansion of the retail footprint.",
                  relevanceScore: 0.8734
                }
              ]}
            />
          </div>
          
          {/* Text Right */}
          <div className="order-1 lg:order-2 max-w-xl">
            <h2 className="font-display text-4xl md:text-5xl font-medium text-text-primary mb-8 leading-tight">
              Research that shows its work.
            </h2>
            <p className="text-text-secondary text-lg leading-relaxed mb-10">
              Unlike generic chatbots, FinSight retrieves verifiable data directly from annual reports and live market feeds. Every claim is cited, and every tool call is visible.
            </p>
            <ul className="space-y-8">
              <li className="flex gap-5">
                <div className="mt-1 w-6 h-6 rounded-full border border-border flex items-center justify-center shrink-0">
                  <span className="text-text-primary text-xs">01</span>
                </div>
                <div>
                  <h3 className="font-medium text-text-primary mb-2 text-base">Live market data</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">Fetches real-time prices and financial ratios for US and Indian equities via yfinance.</p>
                </div>
              </li>
              <li className="flex gap-5">
                <div className="mt-1 w-6 h-6 rounded-full border border-border flex items-center justify-center shrink-0">
                  <span className="text-text-primary text-xs">02</span>
                </div>
                <div>
                  <h3 className="font-medium text-text-primary mb-2 text-base">Cited excerpts</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">Vector search over real annual reports, returning exact paragraphs with verifiable citations.</p>
                </div>
              </li>
              <li className="flex gap-5">
                <div className="mt-1 w-6 h-6 rounded-full border border-border flex items-center justify-center shrink-0">
                  <span className="text-text-primary text-xs">03</span>
                </div>
                <div>
                  <h3 className="font-medium text-text-primary mb-2 text-base">Full reasoning trace</h3>
                  <p className="text-sm text-text-secondary leading-relaxed">See exactly what tools the agent called, their parameters, and how long they took.</p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-8 py-40 max-w-3xl mx-auto text-center">
        <h2 className="font-display text-5xl md:text-6xl font-medium text-text-primary mb-8 leading-tight">
          Ready to elevate your research?
        </h2>
        <p className="text-text-secondary text-lg leading-relaxed mb-12">
          Experience the difference of an AI agent built specifically for deterministic financial analysis.
        </p>
        <Link href="/chat" className="btn-primary px-10 py-4 rounded-lg text-base transition-all hover:shadow-lg inline-block">
          Start researching now
        </Link>
      </section>
      
      {/* Footer */}
      <footer className="py-8 text-center border-t border-border">
        <p className="text-xs text-text-muted font-medium">© {new Date().getFullYear()} FinSight. A portfolio project.</p>
      </footer>
    </div>
  );
}
