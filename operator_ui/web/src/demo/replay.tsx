import { useQuery } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { buildCampaign, viewAt, type CampaignView, type DemoCampaign } from "./campaign";

export const SPEEDS = [10, 30, 90] as const;
const TICK_MS = 100;

interface ReplayState {
  campaign?: DemoCampaign;
  view?: CampaignView;
  t: number;
  playing: boolean;
  speed: number;
  failure: boolean;
  frozen: boolean;
  setPlaying: (playing: boolean) => void;
  setSpeed: (speed: number) => void;
  seek: (t: number) => void;
  setFailure: (failure: boolean) => void;
  setFrozen: (frozen: boolean) => void;
  restart: () => void;
}

const ReplayContext = createContext<ReplayState | null>(null);

// One shared clock drives every live surface, so switching options or pages
// keeps the same moment of the same demo campaign.
export function ReplayProvider({ children }: { children: ReactNode }) {
  const runs = useQuery({ queryKey: ["explorer"], queryFn: api.explorerRuns });
  const [failure, setFailure] = useState(false);
  const campaign = useMemo(() => (runs.data ? buildCampaign(runs.data, failure) : undefined), [runs.data, failure]);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState<number>(30);
  const [frozen, setFrozenState] = useState(false);
  const started = useRef(false);

  // Open mid-campaign so every surface has history to show immediately.
  useEffect(() => {
    if (campaign && !started.current) {
      started.current = true;
      setT(campaign.total * 0.42);
    }
  }, [campaign]);

  useEffect(() => {
    if (!campaign || !playing || frozen) return;
    const id = window.setInterval(() => {
      setT((current) => {
        const next = current + (TICK_MS / 1000) * speed;
        if (next >= campaign.total) {
          setPlaying(false);
          return campaign.total;
        }
        return next;
      });
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [campaign, playing, frozen, speed]);

  const value = useMemo<ReplayState>(() => {
    const clamped = campaign ? Math.min(t, campaign.total) : 0;
    return {
      campaign,
      view: campaign ? viewAt(campaign, clamped) : undefined,
      t: clamped,
      playing: playing && !frozen,
      speed,
      failure,
      frozen,
      setPlaying: (next) => {
        if (next && campaign && t >= campaign.total) setT(0);
        setPlaying(next);
      },
      setSpeed,
      seek: (next) => setT(Math.max(0, campaign ? Math.min(next, campaign.total) : next)),
      setFailure: (next) => {
        setFailure(next);
        if (next && campaign) {
          // Jump to just before the failing attempt so the error is visible.
          const failingStart = campaign.attempts[11]?.end ?? t;
          setT(Math.max(0, failingStart - 2));
          setPlaying(true);
        }
      },
      setFrozen: (next) => {
        setFrozenState(next);
        if (next && campaign) setT(campaign.total * 0.55);
      },
      restart: () => {
        setT(0);
        setPlaying(true);
      },
    };
  }, [campaign, t, playing, speed, failure, frozen]);

  return <ReplayContext.Provider value={value}>{children}</ReplayContext.Provider>;
}

export function useReplay(): ReplayState {
  const value = useContext(ReplayContext);
  if (!value) throw new Error("useReplay must be used inside ReplayProvider");
  return value;
}
