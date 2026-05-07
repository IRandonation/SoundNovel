// ==UserScript==
// @name         番茄小说自动上传助手
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  拖放txt文件自动填充章节标题和内容
// @author       You
// @match        https://author.tomato.com/*
// @match        https://fanqienovel.com/author/*
// @match        https://fanqienovel.com/main/writer/*
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    // 配置：根据实际情况调整选择器
    const CONFIG = {
        // 章节号输入框：在"第"和"章"之间的输入框
        chapterNumSelector: 'input.arco-input, input[type="text"].arco-input-size-large',
        // 章节标题输入框（"请输入标题"那个）
        titleSelector: 'input[placeholder="请输入标题"]',
        // 正文编辑区（番茄使用ProseMirror富文本编辑器）
        contentSelector: '.ProseMirror, .serial-editor-content [contenteditable], div[contenteditable="true"]',
        // 发布按钮的文本内容（用于查找按钮）
        submitButtonTexts: ['发布', '提交', '保存', '立即发布']
    };

    // 创建拖放区域（可拖动）
    function createDropZone() {
        const dropZone = document.createElement('div');
        dropZone.id = 'tomato-dropzone';
        dropZone.innerHTML = `
            <div class="tomato-dropzone-header">
                <span>番茄上传助手</span>
                <span class="drag-handle">⋮⋮</span>
            </div>
            <div class="tomato-dropzone-inner">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <p>拖放章节txt文件到这里</p>
                <p style="font-size: 12px; color: #999;">支持批量上传多个文件</p>
            </div>
        `;
        document.body.appendChild(dropZone);
        makeDraggable(dropZone);
        return dropZone;
    }

    // 使元素可拖动
    function makeDraggable(element) {
        const handle = element.querySelector('.drag-handle') || element.querySelector('.tomato-dropzone-header');
        let isDragging = false;
        let hasMoved = false;
        let startX, startY;
        let currentX = 0;
        let currentY = 0;

        // 鼠标按下开始拖动
        handle.addEventListener('mousedown', (e) => {
            isDragging = true;
            hasMoved = false;
            startX = e.clientX - currentX;
            startY = e.clientY - currentY;
            handle.style.cursor = 'grabbing';
        });

        // 鼠标移动时拖动
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            // 如果移动超过5像素，认为是拖动
            if (Math.abs(dx - currentX) > 5 || Math.abs(dy - currentY) > 5) {
                hasMoved = true;
            }

            currentX = dx;
            currentY = dy;
            element.style.transform = `translate(${currentX}px, ${currentY}px)`;
        });

        // 鼠标松开结束拖动
        document.addEventListener('mouseup', () => {
            isDragging = false;
            handle.style.cursor = 'grab';
        });

        // 点击内容区域时，如果发生了拖动则阻止事件
        element.querySelector('.tomato-dropzone-inner').addEventListener('click', (e) => {
            if (hasMoved) {
                e.stopPropagation();
                e.preventDefault();
                hasMoved = false;
            }
        });

        // 标题栏点击不触发文件选择
        handle.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    // 添加样式
    GM_addStyle(`
        #tomato-dropzone {
            position: fixed;
            top: 50%;
            right: 20px;
            margin-top: -140px;
            width: 280px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 99999;
            overflow: hidden;
            transition: box-shadow 0.3s ease;
        }
        #tomato-dropzone:hover {
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        }
        #tomato-dropzone.dragover {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .tomato-dropzone-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: rgba(0,0,0,0.1);
            color: white;
            font-size: 14px;
            font-weight: 500;
            cursor: grab;
        }
        .tomato-dropzone-header:active {
            cursor: grabbing;
        }
        .drag-handle {
            cursor: grab;
            opacity: 0.7;
            font-size: 12px;
        }
        .drag-handle:hover {
            opacity: 1;
        }
        .tomato-dropzone-inner {
            text-align: center;
            color: white;
            padding: 20px;
            cursor: pointer;
        }
        .tomato-dropzone-inner svg {
            margin-bottom: 10px;
        }
        .tomato-dropzone-inner p {
            margin: 5px 0;
            font-size: 14px;
        }
        .tomato-toast {
            position: fixed;
            top: 180px;
            right: 20px;
            padding: 12px 20px;
            background: #333;
            color: white;
            border-radius: 8px;
            z-index: 99999;
            animation: slideIn 0.3s ease;
        }
        .tomato-toast.success { background: #52c41a; }
        .tomato-toast.error { background: #ff4d4f; }
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `);

    // 显示提示
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `tomato-toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // 解析文件名获取章节信息
    function parseFilename(filename) {
        // 移除 .txt 后缀
        const nameWithoutExt = filename.replace(/\.txt$/i, '');

        // 匹配模式：第0010章 初遇.txt、第10章.txt、chapter_001_初遇.txt 等
        const patterns = [
            // 匹配：第0010章 初遇、第10章 标题
            /^第(\d+)章[\s_-]*(.*)$/,
            // 匹配：chapter_001_初遇、chapter-001 标题
            /^chapter[_-]?(\d+)[_-]?(.*)$/i,
            // 匹配：0010 初遇、10-标题
            /^(\d+)[\s_-]+(.+)$/,
            // 纯数字
            /^(\d+)$/
        ];

        for (const pattern of patterns) {
            const match = nameWithoutExt.match(pattern);
            if (match) {
                const chapterNum = parseInt(match[1], 10);
                const title = match[2]?.trim() || '';
                return { chapterNum, title };
            }
        }

        return { chapterNum: null, title: nameWithoutExt };
    }

    // 从内容第一行解析章节标题
    function parseContentTitle(firstLine) {
        let line = firstLine.trim();

        // 移除 Markdown 标题标记 (# ## ### 等)
        line = line.replace(/^#+\s*/, '');

        // 匹配：第10章 初遇、第0010章：初遇、第十章 初遇
        const patterns = [
            /^第[\d一二三四五六七八九十百千]+章[\s:：]*(.*)$/,
            /^第\d+[\s:：]*(.*)$/,
            /^[Cc]hapter[\s_-]?\d+[\s:：_-]*(.*)$/
        ];

        for (const pattern of patterns) {
            const match = line.match(pattern);
            if (match) {
                return match[1].trim();
            }
        }

        // 如果整行很短且没有标点，可能是标题
        if (line.length < 50 && !line.includes('。') && !line.includes('，')) {
            return line;
        }

        return null;
    }

    // 从内容第一行解析章节号
    function parseContentChapterNum(firstLine) {
        const line = firstLine.trim();

        // 匹配阿拉伯数字
        const match = line.match(/^第(\d+)章/);
        if (match) {
            return parseInt(match[1], 10);
        }

        // 匹配中文数字（简化版）
        const chineseNums = { '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                              '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 };
        const cnMatch = line.match(/^第([一二三四五六七八九十百千]+)章/);
        if (cnMatch) {
            // 简化的中文数字转换，只处理个位数和十位数
            const cnNum = cnMatch[1];
            if (cnNum.length === 1) {
                return chineseNums[cnNum] || null;
            }
            // 例如：十五 -> 15, 二十 -> 20
            let result = 0;
            if (cnNum.includes('十')) {
                const parts = cnNum.split('十');
                if (parts[0]) result += chineseNums[parts[0]] * 10;
                else result += 10;
                if (parts[1]) result += chineseNums[parts[1]] || 0;
                return result;
            }
        }

        return null;
    }

    // 读取文件内容
    function readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file, 'UTF-8');
        });
    }

    // 查找元素（支持多种选择器策略）
    function findElement(selectors) {
        if (typeof selectors === 'string') {
            selectors = [selectors];
        }
        for (const selector of selectors) {
            const el = document.querySelector(selector);
            if (el) return el;
        }
        return null;
    }

    // 模拟真实用户输入，绕过 React 框架控制
    async function simulateUserInput(element, value) {
        if (!element) return false;

        // 聚焦
        element.focus();
        element.click();
        await new Promise(r => setTimeout(r, 100));

        // 选中现有内容
        element.select();
        await new Promise(r => setTimeout(r, 50));

        // 使用原生 setter 绕过 React 控制
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(element, value);

        // 触发完整事件链
        const events = [
            new Event('input', { bubbles: true }),
            new InputEvent('input', { bubbles: true, inputType: 'insertText' }),
            new Event('change', { bubbles: true }),
        ];

        for (const event of events) {
            element.dispatchEvent(event);
            await new Promise(r => setTimeout(r, 50));
        }

        // 模拟 blur
        element.blur();
        await new Promise(r => setTimeout(r, 50));

        return true;
    }

    // 查找章节号输入框（在"第"和"章"之间的那个）
    function findChapterNumInput() {
        // 策略1：查找包含"第"和"章"文本的父元素，然后找其中的输入框
        const allDivs = document.querySelectorAll('div, span, label');

        for (const container of allDivs) {
            const text = container.textContent || '';
            // 检查是否包含"第"和"章"，且中间没有其他文字（只有输入框）
            if (text.includes('第') && text.includes('章')) {
                const inputs = container.querySelectorAll('input');
                if (inputs.length === 1) {
                    console.log('[番茄上传助手] 通过父元素找到章节号输入框:', inputs[0]);
                    return inputs[0];
                }
            }
        }

        // 策略2：查找所有输入框，检查其前面是否有"第"后面是否有"章"
        const allInputs = document.querySelectorAll('input.arco-input, input[type="text"]');

        for (const input of allInputs) {
            const parent = input.parentElement;
            const grandparent = parent?.parentElement;

            // 检查父级文本
            const parentText = parent?.textContent || '';
            const grandparentText = grandparent?.textContent || '';

            // 如果输入框在"第"和"章"之间
            if ((parentText.match(/第.*章/) || grandparentText.match(/第.*章/))) {
                // 排除标题输入框（有placeholder的）
                if (!input.placeholder || input.placeholder === '') {
                    console.log('[番茄上传助手] 通过位置找到章节号输入框:', input);
                    return input;
                }
            }
        }

        // 策略3：如果页面上只有两个主要输入框，取第一个（章节号通常在前面）
        const mainInputs = document.querySelectorAll('input.arco-input-size-large');
        if (mainInputs.length >= 2) {
            // 按Y坐标排序，取最上面的那个
            const sorted = Array.from(mainInputs).sort((a, b) => {
                return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
            });
            console.log('[番茄上传助手] 通过排序找到章节号输入框:', sorted[0]);
            return sorted[0];
        }

        return null;
    }

    // 自动填充表单
    async function fillForm(chapterNum, chapterTitle, content) {
        // 填写章节号（如果有）
        if (chapterNum) {
            const chapterNumInput = findChapterNumInput();

            if (chapterNumInput) {
                const success = await simulateUserInput(chapterNumInput, String(chapterNum));
                if (success) {
                    showToast(`已填写章节号: ${chapterNum}`, 'success');
                }
            } else {
                console.log('[番茄上传助手] 未找到章节号输入框，章节号将包含在标题中');
            }
        }

        // 填写章节标题
        const titleInput = findElement(CONFIG.titleSelector);
        if (titleInput) {
            const success = await simulateUserInput(titleInput, chapterTitle || '');
            if (!success) {
                showToast('标题填写失败', 'error');
                return false;
            }
        } else {
            showToast('未找到标题输入框，请检查配置', 'error');
            return false;
        }

        // 填充正文（等待元素加载）
        let contentInput = findElement(CONFIG.contentSelector);
        let retries = 0;
        while (!contentInput && retries < 10) {
            await new Promise(r => setTimeout(r, 500));
            contentInput = findElement(CONFIG.contentSelector);
            retries++;
        }

        if (contentInput) {
            // 处理 ProseMirror 富文本编辑器
            if (contentInput.classList && contentInput.classList.contains('ProseMirror')) {
                // 清空现有内容
                contentInput.innerHTML = '';
                // 按段落分割，为每行创建 p 标签（ProseMirror 的标准格式）
                const paragraphs = content.split('\n').filter(line => line.trim());
                paragraphs.forEach(text => {
                    const p = document.createElement('p');
                    p.textContent = text;
                    contentInput.appendChild(p);
                });
                // 触发 ProseMirror 的更新事件
                contentInput.dispatchEvent(new InputEvent('input', {
                    bubbles: true,
                    cancelable: true,
                }));
            } else if (contentInput.isContentEditable) {
                contentInput.innerHTML = content.replace(/\n/g, '<br>');
                contentInput.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
                contentInput.value = content;
                contentInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        } else {
            showToast('未找到正文编辑区，请检查配置', 'error');
            return false;
        }

        return true;
    }

    // 查找发布按钮（通过文本内容）
    function findSubmitButton() {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            const text = btn.textContent.trim();
            if (CONFIG.submitButtonTexts.some(t => text.includes(t))) {
                return btn;
            }
        }
        // 备选：查找样式像主按钮的元素
        const primaryBtns = document.querySelectorAll('.arco-btn-primary, .primary-btn, [type="submit"]');
        return primaryBtns[0] || null;
    }

    // 高亮发布按钮（提示用户手动点击）
    function highlightSubmitButton() {
        const submitBtn = findSubmitButton();
        if (submitBtn) {
            // 添加闪烁效果
            submitBtn.style.animation = 'pulse 1s ease-in-out 3';
            GM_addStyle(`
                @keyframes pulse {
                    0%, 100% { box-shadow: 0 0 0 0 rgba(82, 196, 26, 0.7); }
                    50% { box-shadow: 0 0 0 10px rgba(82, 196, 26, 0); }
                }
            `);
            showToast('内容已填充，请手动点击发布按钮', 'success');
        }
    }

    // 处理单个文件
    async function processFile(file) {
        try {
            showToast(`正在读取: ${file.name}`);

            // 读取内容
            const content = await readFile(file);
            const lines = content.split('\n').map(l => l.trim()).filter(l => l);

            // 解析文件名
            const { chapterNum: fileChapterNum, title: fileTitle } = parseFilename(file.name);

            // 尝试从内容第一行解析章节号和标题
            let contentChapterNum = null;
            let contentTitle = null;
            let contentBody = content;

            if (lines.length > 0) {
                const firstLine = lines[0];
                contentChapterNum = parseContentChapterNum(firstLine);
                contentTitle = parseContentTitle(firstLine);

                // 如果第一行是标题，正文从第二行开始
                if (contentChapterNum || contentTitle) {
                    contentBody = lines.slice(1).join('\n');
                }
            }

            // 优先级：文件名 > 内容第一行
            const chapterNum = fileChapterNum || contentChapterNum;
            let chapterTitle = fileTitle || contentTitle || '';

            // 组装标题
            let fullTitle;
            if (chapterNum) {
                // 如果标题已经包含"第X章"，不再重复添加
                if (chapterTitle && !chapterTitle.match(/^第[\d一二三四五六七八九十百千]+章/)) {
                    fullTitle = `第${chapterNum}章 ${chapterTitle}`;
                } else if (chapterTitle) {
                    fullTitle = chapterTitle;
                } else {
                    fullTitle = `第${chapterNum}章`;
                }
            } else {
                fullTitle = chapterTitle || file.name.replace(/\.txt$/i, '');
            }

            console.log('[番茄上传助手] 解析结果:', {
                fileName: file.name,
                chapterNum,
                chapterTitle,
                fullTitle,
                contentLength: contentBody.length
            });

            // 填充表单（分开传递章节号和标题）
            const success = await fillForm(chapterNum, chapterTitle, contentBody);
            if (success) {
                showToast(`已填充: 第${chapterNum || '?'}章 ${chapterTitle || ''}`, 'success');
                highlightSubmitButton();
            }

        } catch (err) {
            console.error('处理文件失败:', err);
            showToast(`读取失败: ${file.name}`, 'error');
        }
    }

    // 初始化拖放功能
    function initDropZone() {
        const dropZone = createDropZone();

        // 阻止默认拖放行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.body.addEventListener(eventName, preventDefaults, false);
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // 高亮效果
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        // 处理拖放
        dropZone.addEventListener('drop', (e) => {
            const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.txt'));

            if (files.length === 0) {
                showToast('请拖放txt文件', 'error');
                return;
            }

            if (files.length === 1) {
                processFile(files[0]);
            } else {
                showToast(`检测到${files.length}个文件，将逐个处理`, 'info');
                // 批量处理：逐个填充（需要页面支持批量）
                files.forEach((file, index) => {
                    setTimeout(() => processFile(file), index * 2000);
                });
            }
        }, false);

        // 点击选择文件
        dropZone.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.txt';
            input.multiple = true;
            input.onchange = (e) => {
                const files = Array.from(e.target.files);
                files.forEach((file, index) => {
                    setTimeout(() => processFile(file), index * 2000);
                });
            };
            input.click();
        });
    }

    // 等待页面加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDropZone);
    } else {
        initDropZone();
    }

    console.log('[番茄上传助手] 已加载，将txt文件拖放到右上角紫色区域即可');
})();
