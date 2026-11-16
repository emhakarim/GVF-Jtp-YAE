#ifndef WEBPAGE_H
#define WEBPAGE_H

#include <Arduino.h>

// ================= HALAMAN WEB PROGMEM MANDIRI (OFFLINE RESILIENT) =================
const char MAIN_page[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 Galileo Controller | 4-Servo Dual-Stage System</title>
    <style>
        :root {
            --bg-page: #f8fafc;
            --bg-card: #ffffff;
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --accent-green: #16a34a;
            --accent-orange: #ea580c;
            --accent-blue: #0284c7;
            --danger: #dc2626;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-page);
            color: var(--text-main);
            padding: 16px;
            max-width: 680px;
            margin: 0 auto;
        }
        .header {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 16px; font-weight: 800; }
        .header p { font-size: 11px; color: var(--text-muted); }
        .badge {
            font-size: 10px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 999px;
            background: #dcfce7;
            color: #15803d;
            border: 1px solid #bbf7d0;
            font-family: monospace;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 14px;
        }
        .card-title {
            font-size: 11px;
            font-weight: 800;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        .btn-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 10px;
        }
        button {
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .btn-stage-1 { background: #ea580c; color: #fff; }
        .btn-stage-2 { background: #334155; color: #fff; }
        .btn-drop-both {
            background: #16a34a;
            color: #fff;
            width: 100%;
            padding: 14px;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .btn-reset { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; width: 100%; margin-bottom: 8px; }
        .btn-carousel-reset { background: #f1f5f9; color: #334155; border: 1px solid var(--border); width: 100%; }
        .info-box {
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 12px;
            font-family: monospace;
            font-size: 11px;
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .terminal {
            background: #090d16;
            color: #38bdf8;
            border-radius: 8px;
            padding: 10px;
            font-family: monospace;
            font-size: 10px;
            height: 120px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>GALILEO CONTROLLER (4-SERVO)</h1>
            <p>ESP32 Direct Portal &bull; Yotta Aksara Energi</p>
        </div>
        <span class="badge" id="wsBadge">WS: CONNECTED</span>
    </div>

    <div class="card">
        <div class="card-title">KENDALI PELEPASAN DUA TAHAP</div>
        
        <div class="info-box">
            <span>Stok Bulu Carousel (Servo 1):</span>
            <strong id="carouselText" style="color: #0284c7;">Slot 1 / 10 (0°)</strong>
        </div>
        <div class="info-box">
            <span>Pintu Bucket (Servo 4):</span>
            <strong id="bucketText" style="color: #16a34a;">TUTUP (Hold)</strong>
        </div>

        <div class="btn-grid">
            <button class="btn-stage-1" onclick="sendCmd('DROP_FEATHER')">1. Muat Bulu (S1+S2)</button>
            <button class="btn-stage-2" onclick="sendCmd('DROP_BALL')">2. Muat Bola (S3)</button>
        </div>

        <button class="btn-drop-both" onclick="sendCmd('DROP_BOTH')">🚀 3. BUKA BUCKET (DROP SIMULTAN - S4)</button>
        <button class="btn-reset" onclick="sendCmd('RESET')">Reset Pintu Bucket (Standby)</button>
        <button class="btn-carousel-reset" onclick="sendCmd('RESET_CAROUSEL')">Reset Carousel Bulu (Slot 1 / 0°)</button>
    </div>

    <div class="card">
        <div class="card-title">LOG TERMINAL HARDWARE</div>
        <div class="terminal" id="termLog">
            <div>[SYSTEM] Menghubungkan ke WebSocket internal ESP32...</div>
        </div>
    </div>

    <script>
        const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProto}//${window.location.host}/ws`);
        const logBox = document.getElementById('termLog');

        function log(msg) {
            const d = document.createElement('div');
            d.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
            logBox.appendChild(d);
            logBox.scrollTop = logBox.scrollHeight;
        }

        ws.onopen = () => {
            document.getElementById('wsBadge').textContent = 'WS: CONNECTED';
            document.getElementById('wsBadge').style.background = '#dcfce7';
            document.getElementById('wsBadge').style.color = '#15803d';
            log('WebSocket aktif terhubung.');
        };

        ws.onclose = () => {
            document.getElementById('wsBadge').textContent = 'WS: DISCONNECTED';
            document.getElementById('wsBadge').style.background = '#fee2e2';
            document.getElementById('wsBadge').style.color = '#dc2626';
            log('WebSocket terputus.');
        };

        ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.event === 'RELEASED') {
                    document.getElementById('bucketText').textContent = 'TERBUKA (Released)';
                    document.getElementById('bucketText').style.color = '#dc2626';
                    log(`BUCKET RELEASED! t_micros=${data.t_drop_micros}`);
                } else if (data.event === 'STAGED') {
                    if (data.target === 'FEATHER') {
                        document.getElementById('carouselText').textContent = `Slot ${data.feather_slot} / 10 (${data.slot_angle}°)`;
                        log(`Bulu dimuat dari slot ${data.feather_slot}`);
                    } else if (data.target === 'BALL') {
                        log('Bola besi dimuat ke bucket.');
                    }
                } else if (data.status === 'MANUAL_RESET_OK') {
                    document.getElementById('bucketText').textContent = 'TUTUP (Hold)';
                    document.getElementById('bucketText').style.color = '#16a34a';
                    log('Pintu bucket ditutup (Standby).');
                } else if (data.status === 'CAROUSEL_RESET') {
                    document.getElementById('carouselText').textContent = 'Slot 1 / 10 (0°)';
                    log('Carousel stok bulu direset ke slot 1.');
                }
            } catch(err) {
                log(e.data);
            }
        };

        function sendCmd(cmd) {
            ws.send(JSON.stringify({ cmd: cmd }));
            log(`Perintah dikirim: ${cmd}`);
        }
    </script>
</body>
</html>
)rawliteral";

#endif // WEBPAGE_H
