/**
 * Per-scenario, per-phase narrative text for the guided tutorial.
 * Short and crisp — 2-3 sentences per field.
 */

export interface PhaseNarrative {
  stage: string;           // matches tool.stage in the backend
  name: string;            // "Phase 1: Reconnaissance"
  subtitle: string;        // "Mapping the battlefield"
  briefing: string;        // what this phase is about
  red: string;             // what Red is doing
  soc: string;             // what SOC should watch for
  blue: string;            // what Blue can do
}

export interface ScenarioStory {
  id: string;
  title: string;
  subtitle: string;
  intro: string;           // opening narrative
  setting: string;
  phases: PhaseNarrative[];
}

export const STORIES: Record<string, ScenarioStory> = {
  "scn-wannacry-w1": {
    id: "scn-wannacry-w1",
    title: "Operation Tripwire",
    subtitle: "WannaCry-Style SMB Worm",
    setting: "Mercy Regional Health Network — 250-host hospital",
    intro: "Friday, 16:42. A radiology workstation that nobody patched in months is about to bring down the entire hospital. You're about to experience the anatomy of a ransomware worm — from the attacker's first scan to the last encrypted file.",
    phases: [
      { stage: "Host Discovery", name: "Phase 1: Reconnaissance", subtitle: "Mapping the battlefield",
        briefing: "Every attack starts with discovery. The worm needs to know what's on the network before it can strike.",
        red: "You're scanning the subnet to find live hosts. This is how every real attack begins — quiet, methodical mapping.",
        soc: "Watch Zeek for horizontal scan patterns — one source hitting many destinations on port 445.",
        blue: "No action yet. The scan is happening, but you may not know it." },
      { stage: "SMB Enumeration", name: "Phase 2: Target Selection", subtitle: "Finding the weak links",
        briefing: "Not every host is vulnerable. The worm looks specifically for SMBv1 — a legacy protocol with a critical flaw.",
        red: "You're identifying which hosts still run the vulnerable SMBv1 protocol. These are your targets.",
        soc: "SMB enumeration may generate subtle traffic. Look for connection attempts on port 445 with SMBv1 negotiation.",
        blue: "If you could see this, you'd want to disable SMBv1 everywhere. But detection hasn't happened yet." },
      { stage: "Exploit", name: "Phase 3: Initial Exploitation", subtitle: "The door opens",
        briefing: "EternalBlue. A buffer overflow in SMBv1 that gives the attacker remote code execution — no password, no user interaction needed.",
        red: "Fire the EternalBlue exploit at a vulnerable host. If it works, you have code execution.",
        soc: "This is your loudest signal. Suricata will fire an exploit signature — don't miss it.",
        blue: "If the SOC escalates, you can isolate the exploited host immediately." },
      { stage: "Payload", name: "Phase 4: Payload Delivery", subtitle: "The worm takes hold",
        briefing: "The exploit gave a shell. Now the attacker drops the actual worm binary and runs it.",
        red: "Deploy the worm payload. Once running, this host becomes the launch pad for everything that follows.",
        soc: "Sysmon shows an unsigned executable spawned from an unusual parent process.",
        blue: "If you isolate now, you contain it to one host. Every second of delay multiplies the damage." },
      { stage: "Persistence", name: "Phase 5: Persistence", subtitle: "Surviving the reboot",
        briefing: "Malware that doesn't survive a reboot is amateur. Real worms install themselves as services or auto-run entries.",
        red: "Install a Windows service so the worm auto-starts at boot. Now reimaging is the only way to clean it.",
        soc: "Sysmon Event ID 6/7: new service created. This is a strong persistence indicator.",
        blue: "Simply rebooting won't help. You need to delete the service AND reimage the host." },
      { stage: "C2", name: "Phase 6: Kill-Switch Check", subtitle: "The worm's secret weakness",
        briefing: "WannaCry checks a hardcoded domain before encrypting. If it resolves, the worm stops. This became the famous accidental kill-switch.",
        red: "The worm checks its kill-switch domain. If it's unreachable, it commits to spreading and encrypting.",
        soc: "DNS logs show a query for a newly-seen, suspicious domain. This is a C2 indicator.",
        blue: "Sinkhole the domain! If you register/redirect it before the worm checks, every infected host goes dormant." },
      { stage: "Lateral Movement", name: "Phase 7: Propagation", subtitle: "One becomes many",
        briefing: "This is what makes WannaCry a WORM. It doesn't wait — it automatically scans and exploits every reachable vulnerable host.",
        red: "Unleash the propagation engine. Watch the red zone expand across VLANs in real-time.",
        soc: "Massive 445/tcp traffic spike. Multiple new IDS alerts. The infection is exponential.",
        blue: "SEGMENT NOW. Cut the VLAN boundaries on port 445. This is the single most effective containment action." },
      { stage: "Disable Recovery", name: "Phase 8: Disable Recovery", subtitle: "Cutting the safety net",
        briefing: "Before encrypting, the worm destroys Windows shadow copies and backup catalogs. No rollback. No undo.",
        red: "Delete shadow copies on all infected hosts. If the backup server is also hit, recovery is impossible.",
        soc: "Sysmon shows vssadmin.exe deleting shadow copies — a critical ransomware precursor.",
        blue: "Protect the backup server (BKP-01) NOW. If it survives, you can recover. If not, you're paying ransom." },
      { stage: "Impact", name: "Phase 9: Encryption", subtitle: "The hospital goes dark",
        briefing: "Files are encrypted with AES-128 + RSA-2048. Ransom notes appear. Radiology can't pull images. The ED goes to paper.",
        red: "Deploy the ransomware. Every infected host encrypts its files and shows the ransom note.",
        soc: "Mass file modification alerts. .WNCRY extension. The incident is now undeniable.",
        blue: "Prevention has failed. Focus on containing what remains and assessing backup viability." },
      { stage: "Contain", name: "Phase 10: Containment & Recovery", subtitle: "Picking up the pieces",
        briefing: "The attack is done. Now it's about how fast you recover — and what you learn.",
        red: "Your mission is complete. The outcome depends on how much spread before defenders contained it.",
        soc: "Build the timeline. Document everything. Your analysis feeds the after-action report.",
        blue: "Restore from backups if they survived. Reimage infected hosts. Patch everything. Brief the board." },
    ],
  },
};

export function getStory(scenarioId: string): ScenarioStory | undefined {
  return STORIES[scenarioId];
}

export function getPhase(scenarioId: string, stage: string): PhaseNarrative | undefined {
  return STORIES[scenarioId]?.phases.find(p => p.stage === stage);
}
