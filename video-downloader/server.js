const express = require('express');
const puppeteer = require('puppeteer');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const fs = require('fs-extra');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 8002;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// Directorio para descargas
const DOWNLOADS_DIR = path.join(__dirname, 'downloads');
fs.ensureDirSync(DOWNLOADS_DIR);

// Estado de las descargas en progreso
const downloadStatus = new Map();

// Función para limpiar archivos antiguos (más de 1 hora)
const cleanupOldFiles = () => {
    const oneHourAgo = Date.now() - (60 * 60 * 1000);
    
    fs.readdir(DOWNLOADS_DIR, (err, files) => {
        if (err) return;
        
        files.forEach(file => {
            const filePath = path.join(DOWNLOADS_DIR, file);
            fs.stat(filePath, (err, stats) => {
                if (err) return;
                if (stats.mtime.getTime() < oneHourAgo) {
                    fs.unlink(filePath, () => {
                        console.log(`🧹 Archivo limpiado: ${file}`);
                    });
                }
            });
        });
    });
};

// Limpiar archivos cada 30 minutos
setInterval(cleanupOldFiles, 30 * 60 * 1000);

// Función principal para descargar video
async function downloadVideoWithPuppeteer(videoUrl, format = 'mp4', downloadId) {
    let browser = null;
    
    try {
        console.log(`🚀 Iniciando descarga: ${downloadId}`);
        downloadStatus.set(downloadId, { status: 'starting', progress: 0, message: 'Iniciando navegador...' });
        
        // Configurar Puppeteer
        browser = await puppeteer.launch({
            headless: 'new',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920x1080'
            ]
        });
        
        const page = await browser.newPage();
        
        // Configurar la página
        await page.setViewport({ width: 1920, height: 1080 });
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36');
        
        downloadStatus.set(downloadId, { status: 'loading', progress: 10, message: 'Cargando kick-video.download...' });
        
        // Ir a kick-video.download
        console.log(`📂 Navegando a kick-video.download...`);
        await page.goto('https://kick-video.download/', { 
            waitUntil: 'networkidle0',
            timeout: 30000 
        });
        
        downloadStatus.set(downloadId, { status: 'filling', progress: 25, message: 'Ingresando URL del video...' });
        
        // Esperar a que cargue el campo de URL
        console.log(`📝 Esperando campo de URL...`);
        await page.waitForSelector('input[placeholder*="URL"], input[type="text"], textarea', { timeout: 10000 });
        
        // Encontrar y llenar el campo de URL
        const urlInput = await page.$('input[placeholder*="URL"], input[type="text"], textarea');
        if (!urlInput) {
            throw new Error('No se encontró el campo de URL');
        }
        
        console.log(`📝 Ingresando URL: ${videoUrl}`);
        await urlInput.click();
        await urlInput.evaluate(input => input.value = '');
        await urlInput.type(videoUrl, { delay: 100 });
        
        downloadStatus.set(downloadId, { status: 'processing', progress: 50, message: 'Procesando video...' });
        
        // Buscar y hacer clic en el botón de descarga
        console.log(`🔍 Buscando botón de descarga...`);
        await page.waitForTimeout(3000); // Esperar más tiempo para que procese
        
        // Primero intentar hacer submit del formulario si existe
        try {
            const form = await page.$('form');
            if (form) {
                console.log(`📝 Enviando formulario...`);
                await form.evaluate(form => form.submit());
                await page.waitForTimeout(5000); // Esperar a que procese
            }
        } catch (e) {
            console.log(`⚠️ No se encontró formulario, buscando botón manualmente...`);
        }
        
        // Función más robusta para encontrar el botón de descarga
        const findDownloadButton = async () => {
            return await page.evaluate(() => {
                // Buscar por texto en todos los elementos clickeables
                const clickableElements = Array.from(document.querySelectorAll(
                    'button, a, input[type="submit"], input[type="button"], div[role="button"], span[role="button"]'
                ));
                
                for (const element of clickableElements) {
                    const text = element.textContent?.toLowerCase() || '';
                    const value = element.value?.toLowerCase() || '';
                    const title = element.title?.toLowerCase() || '';
                    const ariaLabel = element.getAttribute('aria-label')?.toLowerCase() || '';
                    
                    // Palabras clave que indican un botón de descarga
                    const downloadKeywords = [
                        'download', 'descargar', 'get video', 'best quality', 
                        'mp4', 'baixar', 'télécharger', 'scaricare', 'herunterladen'
                    ];
                    
                    const allText = [text, value, title, ariaLabel].join(' ');
                    
                    if (downloadKeywords.some(keyword => allText.includes(keyword))) {
                        return element;
                    }
                }
                
                // Si no encontramos por texto, buscar por posición (botones prominentes)
                const prominentButtons = clickableElements.filter(el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    
                    return rect.width > 100 && rect.height > 30 && 
                           style.display !== 'none' && 
                           style.visibility !== 'hidden';
                });
                
                return prominentButtons[0] || null;
            });
        };
        
        let downloadButton = await findDownloadButton();
        
        if (!downloadButton) {
            // Tomar screenshot para debugging
            await page.screenshot({ 
                path: path.join(DOWNLOADS_DIR, `debug_${downloadId}.png`),
                fullPage: true 
            });
            
            // Obtener información de la página para debugging
            const pageContent = await page.evaluate(() => {
                return {
                    title: document.title,
                    url: window.location.href,
                    buttons: Array.from(document.querySelectorAll('button, a, input')).map(el => ({
                        tag: el.tagName,
                        text: el.textContent?.trim(),
                        type: el.type,
                        class: el.className,
                        id: el.id
                    })).filter(btn => btn.text || btn.type)
                };
            });
            
            console.log(`🐛 Debug info:`, JSON.stringify(pageContent, null, 2));
            throw new Error('No se encontró el botón de descarga. Ver debug screenshot.');
        }
        
        console.log(`✅ Botón encontrado:`, await downloadButton.evaluate(btn => ({
            tag: btn.tagName,
            text: btn.textContent?.trim(),
            class: btn.className
        })));
        
        downloadStatus.set(downloadId, { status: 'downloading', progress: 75, message: 'Iniciando descarga...' });
        
        // Configurar la descarga
        const downloadPath = path.join(DOWNLOADS_DIR, `${downloadId}.${format}`);
        
        await page._client.send('Page.setDownloadBehavior', {
            behavior: 'allow',
            downloadPath: DOWNLOADS_DIR
        });
        
        console.log(`💾 Configurando descarga en: ${downloadPath}`);
        
        // Configurar listener para detectar descargas
        let downloadStarted = false;
        const downloadPromise = new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando descarga'));
            }, 60000); // 1 minuto timeout
            
            page.on('response', async (response) => {
                const url = response.url();
                const contentType = response.headers()['content-type'] || '';
                
                if (contentType.includes('video/') || contentType.includes('application/octet-stream') || 
                    url.includes('.mp4') || url.includes('.mp3')) {
                    downloadStarted = true;
                    clearTimeout(timeout);
                    console.log(`📥 Descarga detectada: ${url}`);
                    resolve(true);
                }
            });
        });
        
        // Hacer clic en el botón de descarga
        console.log(`🖱️ Haciendo clic en botón de descarga...`);
        await downloadButton.click();
        
        // Esperar a que inicie la descarga
        try {
            await downloadPromise;
            console.log(`✅ Descarga iniciada exitosamente`);
        } catch (error) {
            console.log(`⚠️ No se detectó descarga automática, verificando archivos...`);
        }
        
        // Esperar y verificar si se descargó algo
        await page.waitForTimeout(10000);
        
        // Buscar archivos descargados
        const files = await fs.readdir(DOWNLOADS_DIR);
        const videoFiles = files.filter(file => 
            file.includes(downloadId) || 
            (file.endsWith('.mp4') || file.endsWith('.mp3')) &&
            fs.statSync(path.join(DOWNLOADS_DIR, file)).mtime.getTime() > (Date.now() - 60000)
        );
        
        let finalPath = downloadPath;
        if (videoFiles.length > 0) {
            // Encontrar el archivo más reciente
            const latestFile = videoFiles.reduce((latest, current) => {
                const latestPath = path.join(DOWNLOADS_DIR, latest);
                const currentPath = path.join(DOWNLOADS_DIR, current);
                return fs.statSync(currentPath).mtime > fs.statSync(latestPath).mtime ? current : latest;
            });
            
            const oldPath = path.join(DOWNLOADS_DIR, latestFile);
            finalPath = path.join(DOWNLOADS_DIR, `${downloadId}.${format}`);
            
            // Renombrar archivo si es necesario
            if (oldPath !== finalPath) {
                await fs.move(oldPath, finalPath, { overwrite: true });
            }
            
            console.log(`📁 Archivo encontrado y renombrado: ${latestFile} -> ${path.basename(finalPath)}`);
        }
        
        // Verificar que el archivo existe y tiene contenido
        if (await fs.pathExists(finalPath)) {
            const stats = await fs.stat(finalPath);
            if (stats.size > 1000) { // Al menos 1KB
                downloadStatus.set(downloadId, { 
                    status: 'completed', 
                    progress: 100, 
                    message: 'Descarga completada exitosamente', 
                    filePath: finalPath,
                    fileSize: stats.size
                });
                
                console.log(`✅ Descarga completada: ${downloadId} (${(stats.size / 1024 / 1024).toFixed(2)} MB)`);
                
                return {
                    success: true,
                    downloadId,
                    filePath: finalPath,
                    fileSize: stats.size,
                    message: 'Descarga completada exitosamente'
                };
            } else {
                throw new Error('Archivo descargado está vacío o es muy pequeño');
            }
        } else {
            throw new Error('No se pudo completar la descarga');
        }
        
    } catch (error) {
        console.error(`❌ Error en descarga ${downloadId}:`, error.message);
        downloadStatus.set(downloadId, { 
            status: 'error', 
            progress: 0, 
            message: `Error: ${error.message}` 
        });
        
        return {
            success: false,
            downloadId,
            error: error.message
        };
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

// Rutas de la API

// Endpoint de salud
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        service: 'video-downloader',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

// Endpoint para iniciar descarga
app.post('/download', async (req, res) => {
    const { videoUrl, format = 'mp4', title = 'video' } = req.body;
    
    if (!videoUrl) {
        return res.status(400).json({ 
            error: 'URL del video es requerida',
            required_fields: ['videoUrl'],
            optional_fields: ['format', 'title']
        });
    }
    
    if (!['mp4', 'mp3'].includes(format)) {
        return res.status(400).json({ 
            error: 'Formato inválido. Use mp4 o mp3',
            supported_formats: ['mp4', 'mp3']
        });
    }
    
    const downloadId = uuidv4();
    
    console.log(`🎬 Nueva solicitud de descarga: ${downloadId}`);
    console.log(`📹 URL: ${videoUrl}`);
    console.log(`🎵 Formato: ${format}`);
    
    // Iniciar descarga en background
    downloadVideoWithPuppeteer(videoUrl, format, downloadId);
    
    res.json({
        success: true,
        downloadId,
        message: 'Descarga iniciada',
        statusUrl: `/status/${downloadId}`,
        downloadUrl: `/file/${downloadId}`
    });
});

// Endpoint para verificar estado de descarga
app.get('/status/:downloadId', (req, res) => {
    const { downloadId } = req.params;
    const status = downloadStatus.get(downloadId);
    
    if (!status) {
        return res.status(404).json({ 
            error: 'ID de descarga no encontrado',
            downloadId 
        });
    }
    
    res.json({
        downloadId,
        ...status,
        timestamp: new Date().toISOString()
    });
});

// Endpoint para descargar archivo
app.get('/file/:downloadId', (req, res) => {
    const { downloadId } = req.params;
    const status = downloadStatus.get(downloadId);
    
    if (!status) {
        return res.status(404).json({ 
            error: 'ID de descarga no encontrado',
            downloadId 
        });
    }
    
    if (status.status !== 'completed') {
        return res.status(202).json({ 
            error: 'Descarga aún en progreso',
            status: status.status,
            progress: status.progress,
            message: status.message
        });
    }
    
    const filePath = status.filePath;
    
    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ 
            error: 'Archivo no encontrado',
            downloadId 
        });
    }
    
    const filename = path.basename(filePath);
    const fileSize = fs.statSync(filePath).size;
    
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.setHeader('Content-Length', fileSize);
    res.setHeader('Content-Type', 'application/octet-stream');
    
    const fileStream = fs.createReadStream(filePath);
    fileStream.pipe(res);
    
    fileStream.on('end', () => {
        console.log(`📤 Archivo enviado: ${filename}`);
    });
});

// Endpoint para obtener screenshot de debugging
app.get('/debug/:downloadId', (req, res) => {
    const { downloadId } = req.params;
    const screenshotPath = path.join(DOWNLOADS_DIR, `debug_${downloadId}.png`);
    
    if (!fs.existsSync(screenshotPath)) {
        return res.status(404).json({ 
            error: 'Screenshot de debug no encontrado',
            downloadId 
        });
    }
    
    res.setHeader('Content-Type', 'image/png');
    const imageStream = fs.createReadStream(screenshotPath);
    imageStream.pipe(res);
});

// Endpoint para listar descargas activas
app.get('/downloads', (req, res) => {
    const downloads = Array.from(downloadStatus.entries()).map(([id, status]) => ({
        downloadId: id,
        ...status
    }));
    
    res.json({
        total: downloads.length,
        downloads
    });
});

// Middleware de manejo de errores
app.use((error, req, res, next) => {
    console.error('❌ Error del servidor:', error);
    res.status(500).json({ 
        error: 'Error interno del servidor',
        message: error.message 
    });
});

// Manejar rutas no encontradas
app.use('*', (req, res) => {
    res.status(404).json({ 
        error: 'Endpoint no encontrado',
        available_endpoints: [
            'GET /health',
            'POST /download',
            'GET /status/:downloadId',
            'GET /file/:downloadId',
            'GET /debug/:downloadId',
            'GET /downloads'
        ]
    });
});

// Iniciar servidor
app.listen(PORT, () => {
    console.log(`🚀 Video Downloader Service iniciado en puerto ${PORT}`);
    console.log(`📋 Endpoints disponibles:`);
    console.log(`   GET  http://localhost:${PORT}/health`);
    console.log(`   POST http://localhost:${PORT}/download`);
    console.log(`   GET  http://localhost:${PORT}/status/:downloadId`);
    console.log(`   GET  http://localhost:${PORT}/file/:downloadId`);
    console.log(`   GET  http://localhost:${PORT}/debug/:downloadId`);
    console.log(`   GET  http://localhost:${PORT}/downloads`);
    console.log(`📁 Directorio de descargas: ${DOWNLOADS_DIR}`);
    console.log(`🐳 Corriendo en Docker: ${process.env.NODE_ENV === 'production' ? 'SÍ' : 'NO'}`);
    console.log(`🌐 Accessible desde otros contenedores en: http://video-downloader:${PORT}`);
    
    // Limpiar archivos al iniciar
    cleanupOldFiles();
});

// Manejo de cierre graceful
process.on('SIGINT', () => {
    console.log('\n🛑 Cerrando Video Downloader Service...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 Cerrando Video Downloader Service...');
    process.exit(0);
});
