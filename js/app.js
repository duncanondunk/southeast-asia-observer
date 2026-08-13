/* ============================================================
 * 东南亚观察 · app.js
 * 纯原生实现：数据加载 / Markdown 渲染 / 轮播 / 标签筛选 / 目录 / 中英双语
 * 依赖：marked, DOMPurify（CDN 引入，defer 加载）
 * ============================================================ */
(function () {
  'use strict';

  /* ---------- 工具函数 ---------- */
  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ---------- 语言状态 ---------- */
  var LANG = (function () {
    try { return localStorage.getItem('sea-lang') || 'en'; }
    catch (e) { return 'en'; }
  })();

  // 标签中英映射
  var TAG_I18N = {
    '经济产业': 'Economy & Industry', '国家观察': 'Country Watch', '供应链': 'Supply Chain', '量化指数': 'Quantitative Index',
    '地缘政治': 'Geopolitics', '新能源': 'New Energy', '气候变化': 'Climate Change',
    '水资源': 'Water Resources', '南海': 'South China Sea', '华侨华人': 'Overseas Chinese', '侨务': 'Diaspora Affairs', '移民': 'Migration', '历史': 'History', '全球': 'Worldwide', '华南': 'South China',
    '越南': 'Vietnam', '印度尼西亚': 'Indonesia', '新加坡': 'Singapore',
    '菲律宾': 'Philippines', '湄公河流域': 'Mekong Basin',
    '人工智能': 'Artificial Intelligence', '制造业': 'Manufacturing',
    '社会文化': 'Society & Culture', '社会政策': 'Social Policy',
    '马来西亚': 'Malaysia', '缅甸': 'Myanmar', '泰国': 'Thailand', '印尼': 'Indonesia',
    '难民': 'Refugees', '文化遗产': 'Cultural Heritage', '教育': 'Education',
    '环境': 'Environment', '烟霾': 'Haze'
  };
  function tagI18n(t) { return LANG === 'en' ? (TAG_I18N[t] || t) : t; }

  // 按语言取文章字段（英文模式优先 a.en[field]）
  function af(a, field) {
    if (LANG === 'en' && a.en && a.en[field] != null) return a.en[field];
    return a[field];
  }
  // 分类标签统一按中文 category + TAG_I18N 翻译，避免 a.en.category 不一致导致英文首页拆出重复板块
  function categoryLabel(a) {
    var c = a.category || '';
    return LANG === 'en' ? (TAG_I18N[c] || c) : c;
  }
  function authorName() { return LANG === 'en' ? 'Xie Chang' : '谢畅'; }

  // 日期格式化
  function formatDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    if (!m) return iso || '';
    if (LANG === 'en') {
      var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return months[parseInt(m[2], 10) - 1] + ' ' + parseInt(m[3], 10) + ', ' + m[1];
    }
    return parseInt(m[1], 10) + '年' + parseInt(m[2], 10) + '月' + parseInt(m[3], 10) + '日';
  }
  function formatDateShort(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    return m ? (m[1] + '.' + m[2] + '.' + m[3]) : (iso || '');
  }
  function readingLabel(min) {
    return LANG === 'en' ? (min + ' min read') : (min + ' 分钟阅读');
  }

  // 文章 md 文件路径
  function articleFile(a) { return a.file || ('articles/' + a.slug + '.md'); }

  function getQuery(name) {
    var m = new RegExp('[?&]' + name + '=([^&]*)').exec(location.search);
    return m ? decodeURIComponent(m[1]) : null;
  }

  // Markdown 渲染（带安全清洗）
  function renderMarkdown(md) {
    if (typeof marked === 'undefined') return '<p style="color:#a00">Markdown library not loaded.</p>';
    marked.setOptions({ breaks: true, gfm: true });
    var html = marked.parse(md);
    if (typeof DOMPurify !== 'undefined') html = DOMPurify.sanitize(html, { ADD_ATTR: ['target'] });
    return html;
  }
  // 中英分隔：md 内用独占一行的 ===EN=== 分隔，前为中文后为英文
  // 页面 hero 已展示文章标题，正文内去掉第一个 h1，避免重复
  function splitMd(md) {
    var idx = md.search(/\n===EN===\s*\n/);
    var raw;
    if (idx < 0) raw = md;
    else raw = LANG === 'en' ? md.slice(idx).replace(/^\s*===EN===\s*\n/, '') : md.slice(0, idx);
    return raw.replace(/^\s*#\s+[^\n]+\n*/, '');
  }

  /* ---------- 数据加载（带缓存） ---------- */
  var _articlesCache = null;
  function loadArticles() {
    if (_articlesCache) return Promise.resolve(_articlesCache);
    return fetch('data/articles.json')
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (list) {
        list.sort(function (a, b) { return (b.date || '').localeCompare(a.date || ''); });
        _articlesCache = list;
        return list;
      });
  }
  function loadMarkdown(a) {
    return fetch(articleFile(a)).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status); return r.text();
    });
  }

  /* ---------- 静态文本双语切换 ---------- */
  function applyLang() {
    document.documentElement.lang = LANG === 'zh' ? 'zh-CN' : 'en';
    $$('[data-zh]').forEach(function (el) {
      var v = el.getAttribute('data-' + LANG) || el.getAttribute('data-zh') || '';
      if (/<[a-z!/]/i.test(v)) el.innerHTML = v; else el.textContent = v;
    });
    $$('.lang-switch button').forEach(function (b) {
      b.classList.toggle('is-active', b.dataset.lang === LANG);
    });
  }
  function initLangSwitch() {
    var box = $('#langSwitch');
    if (!box) return;
    $$('button', box).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var l = btn.dataset.lang;
        if (l === LANG) return;
        LANG = l;
        try { localStorage.setItem('sea-lang', l); } catch (e) {}
        // 状态从 URL 恢复，reload 保证动态内容按新语言重渲染
        location.reload();
      });
    });
  }

  /* ---------- 通用：移动端导航折叠 ---------- */
  function initNavToggle() {
    var btn = $('#navToggle'), nav = $('#nav');
    if (!btn || !nav) return;
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  /* ---------- 通用：订阅表单 ---------- */
  function initSubscribe() {
    var form = $('#subscribeForm'), msg = $('#subscribeMsg');
    if (!form || !msg) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var email = form.email.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        msg.textContent = LANG === 'en' ? 'Please enter a valid email.' : '请输入有效的邮箱地址。';
        msg.style.color = '#d97734'; return;
      }
      msg.style.color = '';
      msg.textContent = LANG === 'en' ? 'Thanks for subscribing!' : '感谢订阅！我们会在每周一封送出。';
      form.reset();
    });
  }

  /* ============================================================
   * 首页
   * ============================================================ */
  function initHome() {
    if (!$('#carouselTrack')) return;
    loadArticles()
      .then(function (list) {
        renderCarousel(list.slice(0, 5)); // 精选 hero 轮播：全站最新发布的 5 篇
        renderLatest(list.slice(0, 3)); // 最新文章板块：仅展示全站最新发布的前 3 篇（list 已按 date 倒序）
        renderRanking(list);
        renderCategorySections(list);
        initShareWidgets(); // 数据专题卡片等静态区块的微信/微博分享按钮
      })
      .catch(function (err) {
        console.error('load articles failed:', err);
        var lb = $('#latestList');
        if (lb) lb.innerHTML = '<div class="empty"><div class="empty__emoji">📭</div>' +
          (LANG === 'en' ? 'Failed to load. Serve via a local HTTP server (python3 -m http.server).' : '文章加载失败，请通过本地服务器访问。') + '</div>';
      });
  }

  function renderCarousel(featured) {
    var track = $('#carouselTrack'), dotsBox = $('#carouselDots');
    if (!track) return;
    if (!featured.length) {
      track.innerHTML = '<div class="slide slide--a"><div class="slide__overlay"></div><div class="slide__content"><div class="slide__title">' + (LANG === 'en' ? 'No featured' : '暂无精选') + '</div></div></div>';
      return;
    }
    var slideClasses = ['slide--a', 'slide--b', 'slide--c'];
    track.innerHTML = featured.map(function (a, i) {
      var bg = a.image ? ('style="background-image:url(' + escapeHtml(a.image) + ');"') : '';
      return '' +
        '<div class="slide ' + slideClasses[i % 3] + '" ' + bg + '>' +
          '<div class="slide__overlay"></div>' +
          '<div class="slide__content">' +
            '<span class="slide__cat">' + escapeHtml(categoryLabel(a)) + '</span>' +
            '<h2 class="slide__title"><a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + escapeHtml(af(a, 'title')) + '</a></h2>' +
            '<div class="slide__meta">' + formatDate(a.date) + ' · ' + readingLabel(a.readingTime || 5) + ' · <a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + (LANG === 'en' ? 'Read full →' : '阅读全文 →') + '</a></div>' +
          '</div>' +
        '</div>';
    }).join('');

    dotsBox.innerHTML = featured.map(function (_, i) {
      return '<button class="carousel__dot' + (i === 0 ? ' is-active' : '') + '" data-i="' + i + '" aria-label="' + (i + 1) + '"></button>';
    }).join('');

    var idx = 0, total = featured.length;
    function go(i) {
      idx = (i + total) % total;
      track.style.transform = 'translateX(-' + (idx * 100) + '%)';
      $$('.carousel__dot', dotsBox).forEach(function (d, di) { d.classList.toggle('is-active', di === idx); });
    }
    $('#carouselPrev').addEventListener('click', function () { go(idx - 1); resetTimer(); });
    $('#carouselNext').addEventListener('click', function () { go(idx + 1); resetTimer(); });
    $$('.carousel__dot', dotsBox).forEach(function (d) {
      d.addEventListener('click', function () { go(parseInt(d.dataset.i, 10)); resetTimer(); });
    });
    var timer = null;
    function startTimer() { timer = setInterval(function () { go(idx + 1); }, 5000); }
    function resetTimer() { clearInterval(timer); startTimer(); }
    var carousel = $('#carousel');
    carousel.addEventListener('mouseenter', function () { clearInterval(timer); });
    carousel.addEventListener('mouseleave', startTimer);
    startTimer();
  }

  function renderLatest(list) {
    var box = $('#latestList'); if (!box) return;
    box.innerHTML = list.map(function (a, i) { return articleCardHtml(a, (i % 5) + 1); }).join('');
  }

  function renderRanking(list) {
    var box = $('#rankingList'); if (!box) return;
    box.innerHTML = list.slice(0, 5).map(function (a, i) {
      return '<div class="ranking__item"><div class="ranking__num">' + (i + 1) + '</div><div class="ranking__body">' +
        '<h4 class="ranking__name"><a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + escapeHtml(af(a, 'title')) + '</a></h4>' +
        '<div class="ranking__date">' + formatDateShort(a.date) + '</div></div></div>';
    }).join('');
  }

  // 分享平台 SVG 图标（inline，统一尺寸与视觉风格）
  var ICON_WECHAT = '<svg class="share-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8.5 2C4.91 2 2 4.24 2 7c0 1.4.72 2.66 1.86 3.52L3.5 13l2.36-1.18C6.54 11.64 7.26 11.74 8 11.74c.12 0 .24 0 .36-.01-.23-.66-.35-1.36-.35-2.09 0-3.04 2.55-5.5 5.7-5.5.23 0 .46.02.68.05C14.1 2.95 11.5 2 8.5 2zm5.7 5c-2.87 0-5.2 2.01-5.2 4.5s2.33 4.5 5.2 4.5c.6 0 1.18-.08 1.73-.22L21.5 16l-.27-2.08c.93-.72 1.47-1.74 1.47-2.87 0-2.49-2.33-4.5-5.2-4.5h-.3zm-2.1 2.5c.39 0 .7.31.7.7s-.31.7-.7.7-.7-.31-.7-.7.31-.7.7-.7zm4.2 0c.39 0 .7.31.7.7s-.31.7-.7.7-.7-.31-.7-.7.31-.7.7-.7z" fill="currentColor"/></svg>';
  var ICON_WEIBO = '<svg class="share-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M10.5 3C6.36 3 3 5.5 3 8.5c0 2.2 1.6 4.1 4 5l-.4 1.5 2.2-1.2c.7.18 1.45.28 2.2.28.5 0 .95-.04 1.4-.1-.3-.85-.45-1.75-.45-2.7 0-3.4 2.65-6.18 5.95-6.6-.9-1.2-3.3-1.8-5.4-1.8zm-2 6.5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5-1.5-.67-1.5-1.5.67-1.5 1.5-1.5zm6.5-3.5c.6 0 1 .4 1 1s-.4 1-1 1-1-.4-1-1 .4-1 1-1zm1.5 1c.3 0 .5.2.5.5s-.2.5-.5.5-.5-.2-.5-.5.2-.5.5-.5z" fill="currentColor"/></svg>';

  function shareBarHtml(url, title) {
    var text = encodeURIComponent(title + ' · Southeast Asia Watch');
    var u = encodeURIComponent(url);
    var wechatLabel = LANG === 'en' ? 'WeChat' : '微信';
    var weiboLabel = LANG === 'en' ? 'Weibo' : '微博';
    var mailLabel = LANG === 'en' ? 'Email' : '邮件';
    return '<div class="article-card__share">' +
      '<a href="https://twitter.com/intent/tweet?text=' + text + '&url=' + u + '" target="_blank" rel="noopener" title="X">𝕏</a>' +
      '<a href="https://www.facebook.com/sharer/sharer.php?u=' + u + '" target="_blank" rel="noopener" title="Facebook">f</a>' +
      '<a href="mailto:?subject=' + text + '&body=' + encodeURIComponent('Recommended: ') + u + '" title="' + mailLabel + '">✉</a>' +
      '<button type="button" class="share-wechat" data-share-url="' + escapeHtml(url) + '" data-share-title="' + escapeHtml(title) + '" title="' + wechatLabel + '">' + ICON_WECHAT + '</button>' +
      '<a href="https://service.weibo.com/share/share.php?url=' + u + '&title=' + text + '" target="_blank" rel="noopener" title="' + weiboLabel + '">' + ICON_WEIBO + '</a>' +
    '</div>';
  }

  function articleCardHtml(a, coverSeed) {
    var coverClass = a.image ? 'has-image' : ('article-card__cover--' + (((coverSeed || 1) - 1) % 5 + 1));
    var coverImg = a.image ? ('<img class="cover__img" src="' + escapeHtml(a.image) + '" alt="" decoding="async" onerror="this.style.display=\'none\'">') : '';
    var share = shareLinks(a);
    return '' +
      '<article class="article-card">' +
        '<a class="article-card__cover ' + coverClass + '" href="article.html?slug=' + encodeURIComponent(a.slug) + '" aria-label="' + escapeHtml(af(a, 'title')) + '">' +
          coverImg +
          '<span class="cover__tag">' + escapeHtml(af(a, 'country') || categoryLabel(a)) + '</span>' +
        '</a>' +
        '<div class="article-card__body">' +
          shareBarHtml(share.url, af(a, 'title')) +
          '<div class="article-card__cat">' + escapeHtml(categoryLabel(a)) + '</div>' +
          '<h3 class="article-card__title"><a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + escapeHtml(af(a, 'title')) + '</a></h3>' +
          '<p class="article-card__excerpt">' + escapeHtml(af(a, 'summary') || af(a, 'subtitle') || '') + '</p>' +
          '<div class="article-card__meta">' +
            '<span class="author">' + escapeHtml(authorName()) + '</span>' +
            '<span>' + formatDate(a.date) + '</span>' +
            '<span>' + readingLabel(a.readingTime || 5) + '</span>' +
          '</div>' +
        '</div>' +
      '</article>';
  }

  function renderCategorySections(list) {
    var box = $('#categorySections'); if (!box) return;
    // 统一按中文 category 分组，再用 categoryLabel 翻译标题，避免 a.en.category 不一致拆出重复板块
    var groups = {};
    list.forEach(function (a) { var c = a.category || ''; if (c) (groups[c] = groups[c] || []).push(a); });
    var order = ['华侨华人', '地缘政治', '经济产业', '气候变化', '社会文化'];
    var cats = Object.keys(groups).sort(function (x, y) {
      var ix = order.indexOf(x), iy = order.indexOf(y);
      return (ix < 0 ? 99 : ix) - (iy < 0 ? 99 : iy);
    });
    var html = '';
    cats.forEach(function (cat, ci) {
      // 每个板块仅展示该分类下最新发布的前三篇
      var items = groups[cat].slice().sort(function (a, b) { return (b.date || '').localeCompare(a.date || ''); });
      var top3 = items.slice(0, 3);
      var top5 = items.slice(0, 5); // 本分类热读侧栏：最多展示 5 篇
      var isAlt = ci % 2 === 1;
      html += '<section class="section' + (isAlt ? ' section--alt' : '') + '"><div class="container">';
      html += '<div class="section__head"><h2 class="section__title">' + escapeHtml(categoryLabel({category: cat})) + '</h2><a class="section__more" href="tags.html?tag=' + encodeURIComponent(cat) + '">' + (LANG === 'en' ? 'View all →' : '查看全部 →') + '</a></div>';
      html += '<div class="cat-grid"><div class="article-list">';
      top3.forEach(function (a, i) { html += articleCardHtml(a, ci * 10 + i + 1); });
      html += '</div><aside class="ranking"><h3 class="ranking__title">' + (LANG === 'en' ? 'Top in section' : '本分类热读') + ' <span>Most Read</span></h3><div>';
      top5.forEach(function (a, i) {
        html += '<div class="ranking__item"><div class="ranking__num">' + (i + 1) + '</div><div class="ranking__body"><h4 class="ranking__name"><a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + escapeHtml(af(a, 'title')) + '</a></h4><div class="ranking__date">' + formatDateShort(a.date) + '</div></div></div>';
      });
      html += '</div></aside></div></div></section>';
    });
    box.innerHTML = html;
  }

  /* ============================================================
   * 文章详情
   * ============================================================ */
  function initArticle() {
    if (!$('#articleTitle')) return;
    var slug = getQuery('slug');
    if (!slug) {
      $('#articleTitle').textContent = LANG === 'en' ? 'No article specified' : '未指定文章';
      $('#articleBody').innerHTML = '<div class="empty"><div class="empty__emoji">🔍</div>' +
        (LANG === 'en' ? 'Pick an article from the ' : '请从') + '<a href="index.html">' + (LANG === 'en' ? 'home page' : '首页') + '</a>' + (LANG === 'en' ? '.' : '选择一篇文章。') + '</div>';
      return;
    }
    loadArticles()
      .then(function (list) {
        var idx = list.findIndex(function (a) { return a.slug === slug; });
        if (idx < 0) throw new Error('Article not found: ' + slug);
        var a = list[idx];
        document.title = af(a, 'title') + ' · ' + (LANG === 'en' ? 'Southeast Asia Watch' : '东南亚观察');
        var descMeta = document.querySelector('meta[name="description"]');
        if (descMeta) descMeta.setAttribute('content', af(a, 'summary') || af(a, 'subtitle') || '');

        $('#articleCat').textContent = categoryLabel(a);
        $('#articleTitle').textContent = af(a, 'title');
        $('#articleSub').textContent = af(a, 'subtitle') || '';
        $('#articleMeta').innerHTML =
          '<span>' + escapeHtml(authorName()) + '</span><span class="sep">|</span>' +
          '<span>' + formatDate(a.date) + '</span><span class="sep">|</span>' +
          '<span>' + readingLabel(a.readingTime || 5) + '</span><span class="sep">|</span>' +
          '<span>' + escapeHtml(af(a, 'country') || '') + '</span>';

        var heroImg = $('#articleHeroImage');
        if (heroImg && a.image) {
          heroImg.innerHTML = '<img src="' + escapeHtml(a.image) + '" alt="' + escapeHtml(af(a, 'imageAlt') || '') + '">';
        }

        var tagsHtml = (a.tags || []).map(function (t) {
          return '<a class="tag" href="tags.html?tag=' + encodeURIComponent(t) + '">' + escapeHtml(tagI18n(t)) + '</a>';
        }).join('');
        $('#articleTags').innerHTML = tagsHtml;

        initArticleShare(a);

        return loadMarkdown(a).then(function (md) {
          var body = $('#articleBody');
          body.innerHTML = renderMarkdown(splitMd(md));
          if (a.image) insertArticleFigure(body, a);
          $$('h2, h3', body).forEach(function (h, i) { h.id = 'sec-' + i; });
          buildToc(body);
          buildPostNav(list, idx);
          renderReferences(a);
          initComments(slug);
        });
      })
      .catch(function (err) {
        console.error('article load failed:', err);
        $('#articleTitle').textContent = LANG === 'en' ? 'Load failed' : '加载失败';
        $('#articleBody').innerHTML = '<div class="empty"><div class="empty__emoji">⚠️</div>' +
          (LANG === 'en' ? 'Failed: ' : '文章加载失败：') + escapeHtml(err.message) + '</div>';
      });
  }

  function buildToc(body) {
    var tocList = $('#tocList'), tocBox = $('#toc');
    if (!tocList) return;
    var heads = $$('h2, h3', body);
    if (!heads.length) { if (tocBox) tocBox.style.display = 'none'; return; }
    tocList.innerHTML = heads.map(function (h) {
      var level = h.tagName === 'H2' ? '' : ' style="padding-left:24px;font-size:.82rem;"';
      return '<li' + level + '><a href="#' + h.id + '">' + escapeHtml(h.textContent) + '</a></li>';
    }).join('');
  }

  function buildPostNav(list, idx) {
    var box = $('#postNav'); if (!box) return;
    var prev = list[idx + 1], next = list[idx - 1];
    var html = '';
    if (prev) html += '<a class="post-nav--prev" href="article.html?slug=' + encodeURIComponent(prev.slug) + '"><div class="post-nav__dir">' + (LANG === 'en' ? '← Previous' : '← 上一篇') + '</div><div class="post-nav__title">' + escapeHtml(af(prev, 'title')) + '</div></a>';
    else html += '<span></span>';
    if (next) html += '<a class="post-nav--next" href="article.html?slug=' + encodeURIComponent(next.slug) + '"><div class="post-nav__dir">' + (LANG === 'en' ? 'Next →' : '下一篇 →') + '</div><div class="post-nav__title">' + escapeHtml(af(next, 'title')) + '</div></a>';
    else html += '<span></span>';
    box.innerHTML = html;
  }

  function renderReferences(a) {
    var box = $('#articleRefs');
    if (!box) return;
    var refs = a.references;
    if (!refs || !refs.length) { box.style.display = 'none'; return; }
    var heading = LANG === 'en' ? 'References' : '参考来源';
    var note = LANG === 'en'
      ? 'Authoritative media reports consulted (within the past week where available).'
      : '本文参考的权威媒体报道（尽可能采用近一周来源）。';
    var items = refs.map(function (r) {
      return '<li class="article-refs__item">' +
        '<a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(r.title) + '</a>' +
        '<span class="article-refs__meta">' + escapeHtml(r.source || '') + (r.date ? ' · ' + escapeHtml(r.date) : '') + '</span>' +
        '</li>';
    }).join('');
    box.innerHTML =
      '<h2 class="article-refs__title">' + heading + '</h2>' +
      '<p class="article-refs__note">' + note + '</p>' +
      '<ul class="article-refs__list">' + items + '</ul>';
  }

  function shareLinks(a) {
    var url = location.origin + location.pathname.replace(/[^/]*$/, '') + 'article.html?slug=' + encodeURIComponent(a.slug);
    var text = encodeURIComponent(af(a, 'title') + ' · Southeast Asia Watch');
    var u = encodeURIComponent(url);
    return {
      url: url,
      x: 'https://twitter.com/intent/tweet?text=' + text + '&url=' + u,
      fb: 'https://www.facebook.com/sharer/sharer.php?u=' + u,
      weibo: 'https://service.weibo.com/share/share.php?url=' + u + '&title=' + text,
      mail: 'mailto:?subject=' + text + '&body=' + encodeURIComponent('Recommended: ') + u
    };
  }

  // 微信分享：弹出二维码，用户用微信扫码分享（桌面 Web 无直接分享接口）
  function openWechatModal(shareUrl) {
    var modal = $('#wechatModal');
    if (!modal) return;
    var abs = shareUrl;
    try { abs = new URL(shareUrl, location.href).href; } catch (e) {}
    var urlEl = $('#wechatModalUrl'); if (urlEl) urlEl.textContent = abs;
    var box = $('#wechatQr');
    if (box) {
      box.innerHTML = '';
      if (typeof QRCode !== 'undefined') {
        try {
          new QRCode(box, {
            text: abs, width: 200, height: 200,
            colorDark: '#1f1b16', colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.M
          });
        } catch (err) {
          box.innerHTML = '<p style="color:#c0392b">' + (LANG === 'en' ? 'QR generation failed' : '二维码生成失败') + '</p>';
        }
      } else {
        box.innerHTML = '<p style="color:#c0392b">' + (LANG === 'en' ? 'QR library not loaded' : '二维码组件未加载') + '</p>';
      }
    }
    modal.removeAttribute('hidden');
    modal.classList.add('is-open');
  }
  function closeWechatModal() {
    var modal = $('#wechatModal');
    if (modal) { modal.setAttribute('hidden', ''); modal.classList.remove('is-open'); }
  }

  // 为带 data-wechat / data-weibo 属性的分享按钮绑定交互（数据专题卡片等静态区块使用）
  function initShareWidgets() {
    // 静态 data-wechat 按钮（兼容旧版数据专题卡片）
    $$('[data-wechat]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var url = btn.getAttribute('data-wechat');
        try { url = new URL(url, location.href).href; } catch (e) {}
        openWechatModal(url);
      });
    });
    $$('[data-weibo]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var abs = btn.getAttribute('data-weibo');
        try { abs = new URL(abs, location.href).href; } catch (e) {}
        var u = encodeURIComponent(abs);
        var t = encodeURIComponent(btn.getAttribute('data-weibo-title') || '');
        window.open('https://service.weibo.com/share/share.php?url=' + u + '&title=' + t, '_blank', 'noopener');
      });
    });
    bindModalClose();
    bindShareDelegation();
  }

  // 全局事件委托：统一处理动态生成的文章卡片与数据专题卡片上的微信弹窗按钮
  function bindShareDelegation() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('.share-wechat');
      if (!btn) return;
      e.preventDefault();
      var url = btn.getAttribute('data-share-url');
      try { url = new URL(url, location.href).href; } catch (e) {}
      openWechatModal(url);
    });
  }

  // 绑定微信分享弹窗的关闭按钮、背景点击、ESC 关闭
  function bindModalClose() {
    var modal = $('#wechatModal');
    if (!modal) return;
    if (modal.dataset.closeBound) return;
    modal.dataset.closeBound = 'true';
    $$('#wechatModal [data-close]').forEach(function (el) {
      el.addEventListener('click', closeWechatModal);
    });
    modal.addEventListener('click', function (e) {
      if (e.target === modal || e.target.classList.contains('modal__backdrop')) closeWechatModal();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !modal.hidden) closeWechatModal();
    });
  }

  function initArticleShare(a) {
    var s = shareLinks(a);
    bindModalClose();
    $('#shareX').href = s.x; $('#shareFb').href = s.fb; $('#shareMail').href = s.mail;
    if ($('#shareWeibo')) $('#shareWeibo').href = s.weibo;
    if ($('#shareWechat')) {
      $('#shareWechat').addEventListener('click', function (e) {
        e.preventDefault(); openWechatModal(s.url);
      });
    }
    var copy = $('#copyLink');
    copy.addEventListener('click', function (e) {
      e.preventDefault();
      var raw = location.href;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(raw).then(function () {
          copy.textContent = LANG === 'en' ? 'Copied ✓' : '已复制 ✓';
          setTimeout(function () { copy.textContent = LANG === 'en' ? 'Copy link' : '复制链接'; }, 1800);
        });
      }
    });
  }

  /* ---------- 文章评论（基于 localStorage 的纯前端留言板） ---------- */
  function commentStorageKey(slug) { return 'sea-comments-' + slug; }
  function commentAuthorKey() { return 'sea-comment-author'; }
  function loadSavedAuthor() {
    try { return JSON.parse(localStorage.getItem(commentAuthorKey()) || '{}'); } catch (e) { return {}; }
  }
  function saveAuthorProfile(profile) {
    try { localStorage.setItem(commentAuthorKey(), JSON.stringify(profile)); } catch (e) {}
  }
  function getComments(slug) {
    try { return JSON.parse(localStorage.getItem(commentStorageKey(slug)) || '[]'); } catch (e) { return []; }
  }
  function pushComment(slug, comment) {
    var list = getComments(slug);
    list.unshift(comment);
    try { localStorage.setItem(commentStorageKey(slug), JSON.stringify(list)); } catch (e) {}
  }
  function renderCommentsList(slug) {
    var box = $('#commentsList'); if (!box) return;
    var list = getComments(slug);
    if (!list.length) {
      box.innerHTML = '<p class="comments__empty" data-zh="暂无评论，欢迎发表第一条评论。" data-en="No comments yet. Be the first to leave a reply.">暂无评论，欢迎发表第一条评论。</p>';
      return;
    }
    box.innerHTML = '<h3 class="comments__count">' + list.length + (LANG === 'en' ? ' comment' + (list.length > 1 ? 's' : '') : ' 条评论') + '</h3>' +
      list.map(function (c, i) {
        return '<article class="comment" id="comment-' + i + '">' +
          '<div class="comment__header">' +
            '<span class="comment__author">' + escapeHtml(c.name) + '</span>' +
            (c.website ? '<a class="comment__site" href="' + escapeHtml(c.website) + '" target="_blank" rel="noopener">' + (LANG === 'en' ? 'Website' : '网站') + '</a>' : '') +
            '<span class="comment__date">' + formatDate(c.date) + '</span>' +
          '</div>' +
          '<div class="comment__body">' + escapeHtml(c.comment).replace(/\n/g, '<br>') + '</div>' +
        '</article>';
      }).join('');
  }
  function initComments(slug) {
    var section = $('#comments'); if (!section) return;
    var form = $('#commentsForm'); if (!form) return;
    renderCommentsList(slug);
    var saved = loadSavedAuthor();
    if (saved.name && $('#commentName')) $('#commentName').value = saved.name;
    if (saved.email && $('#commentEmail')) $('#commentEmail').value = saved.email;
    if (saved.website && $('#commentWebsite')) $('#commentWebsite').value = saved.website;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var bodyEl = $('#commentBody'), nameEl = $('#commentName'), emailEl = $('#commentEmail'), websiteEl = $('#commentWebsite'), saveEl = $('#commentSave'), statusEl = $('#commentStatus');
      var comment = { comment: (bodyEl ? bodyEl.value : '').trim(), name: (nameEl ? nameEl.value : '').trim(), email: (emailEl ? emailEl.value : '').trim(), website: (websiteEl ? websiteEl.value : '').trim(), date: new Date().toISOString().slice(0, 10) };
      if (!comment.comment || !comment.name || !comment.email) {
        if (statusEl) { statusEl.textContent = LANG === 'en' ? 'Please fill in the required fields.' : '请填写必填项。'; statusEl.className = 'comments__status comments__status--error'; }
        return;
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(comment.email)) {
        if (statusEl) { statusEl.textContent = LANG === 'en' ? 'Please enter a valid email address.' : '请输入有效的邮箱地址。'; statusEl.className = 'comments__status comments__status--error'; }
        return;
      }
      pushComment(slug, comment);
      if (saveEl && saveEl.checked) saveAuthorProfile({ name: comment.name, email: comment.email, website: comment.website });
      form.reset();
      if (saved.name && $('#commentName')) $('#commentName').value = saved.name;
      if (saved.email && $('#commentEmail')) $('#commentEmail').value = saved.email;
      if (saved.website && $('#commentWebsite')) $('#commentWebsite').value = saved.website;
      renderCommentsList(slug);
      if (statusEl) { statusEl.textContent = LANG === 'en' ? 'Your comment has been posted. Thank you!' : '评论已发表，谢谢！'; statusEl.className = 'comments__status comments__status--success'; }
      setTimeout(function () { if (statusEl) { statusEl.textContent = ''; statusEl.className = 'comments__status'; } }, 4000);
    });
  }

  function insertArticleFigure(body, a) {
    var firstP = body.querySelector('p');
    if (!firstP) return;
    var fig = document.createElement('figure');
    fig.className = 'article-figure';
    var credit = escapeHtml(a.imageCredit || 'Pexels');
    var accessed = formatDate(a.imageAccessed || a.date);
    var cap = LANG === 'en'
      ? ('Image source: ' + credit + '. Accessed ' + accessed + '.')
      : ('图片来源：' + credit + '，访问时间：' + accessed + '。');
    fig.innerHTML =
      '<img src="' + escapeHtml(a.image) + '" alt="' + escapeHtml(af(a, 'imageAlt') || '') + '">' +
      '<figcaption>' + cap + '</figcaption>';
    firstP.parentNode.insertBefore(fig, firstP.nextSibling);
  }

  /* ============================================================
   * 标签页
   * ============================================================ */
  function initTags() {
    if (!$('#tagCloud')) return;
    var currentTag = getQuery('tag');
    loadArticles()
      .then(function (list) {
        var counts = {};
        list.forEach(function (a) { (a.tags || []).forEach(function (t) { counts[t] = (counts[t] || 0) + 1; }); });
        var tags = Object.keys(counts).sort(function (x, y) { return counts[y] - counts[x]; });
        $('#tagCloud').innerHTML = tags.map(function (t) {
          return '<a class="tag" href="tags.html?tag=' + encodeURIComponent(t) + '">' + escapeHtml(tagI18n(t)) + '<span class="tag-count">' + counts[t] + '</span></a>';
        }).join('');
        applyFilter(currentTag, list);
        updateTagsHero(currentTag);
      })
      .catch(function (err) {
        console.error('tags load failed:', err);
        $('#gridList').innerHTML = '<div class="empty">' + (LANG === 'en' ? 'Load failed' : '加载失败') + '</div>';
      });
  }

  function updateTagsHero(tag) {
    var title = $('#tagsHeroTitle');
    var subtitle = $('#tagsHeroSubtitle');
    if (!title || !tag) return;
    var label = tagI18n(tag);
    title.textContent = label;
    if (subtitle) {
      subtitle.textContent = LANG === 'en'
        ? 'Articles tagged with "' + escapeHtml(label) + '"'
        : '「' + escapeHtml(label) + '」相关文章';
    }
  }

  function applyFilter(tag, list) {
    var box = $('#gridList');
    // tag 是中文键；筛选时按原始中文 tag 匹配
    // tag 是中文键；按原始中文 tag 匹配（tags 中含该标签，或文章分类即该标签），保证分类导航页完整
    var filtered = tag ? list.filter(function (a) { return (a.tags || []).indexOf(tag) !== -1 || a.category === tag; }) : list;
    if (!filtered.length) {
      box.innerHTML = '<div class="empty" style="grid-column:1/-1;"><div class="empty__emoji">🗂️</div>' +
        (LANG === 'en' ? 'No articles for "' + escapeHtml(tag ? tagI18n(tag) : '') + '".' : '暂无「' + escapeHtml(tag || '') + '」相关文章。') + '</div>';
      return;
    }
    box.innerHTML = filtered.map(function (a) {
      return '<article class="grid-card">' +
        '<div class="grid-card__cat">' + escapeHtml(categoryLabel(a)) + ' · ' + escapeHtml(af(a, 'country') || '') + '</div>' +
        '<h3 class="grid-card__title"><a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + escapeHtml(af(a, 'title')) + '</a></h3>' +
        '<p class="grid-card__excerpt">' + escapeHtml(af(a, 'summary') || af(a, 'subtitle') || '') + '</p>' +
        '<div class="grid-card__meta"><span>' + formatDateShort(a.date) + '</span><span>' + readingLabel(a.readingTime || 5) + '</span></div>' +
      '</article>';
    }).join('');
    $$('#tagCloud .tag').forEach(function (a) {
      var m = /tag=([^&]*)/.exec(a.getAttribute('href') || '');
      a.classList.toggle('tag--accent', m && decodeURIComponent(m[1]) === tag);
    });
  }

  /* ============================================================
   * 启动
   * ============================================================ */
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  /* ---------- 首页照片轮播（全宽，参考深职大布局） ---------- */
  function initHeroBanner() {
    var slides = $$('.hero-banner__slide');
    var dots = $$('.hero-banner__dot');
    var prevBtn = $('#bannerPrev');
    var nextBtn = $('#bannerNext');
    if (!slides.length) return;

    var current = 0;
    var timer = null;
    var INTERVAL = 5000; // 5 秒自动切换

    function goTo(index) {
      slides[current].classList.remove('is-active');
      dots[current].classList.remove('is-active');
      current = (index + slides.length) % slides.length;
      slides[current].classList.add('is-active');
      dots[current].classList.add('is-active');
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    function startAuto() {
      stopAuto();
      timer = setInterval(next, INTERVAL);
    }
    function stopAuto() {
      if (timer) { clearInterval(timer); timer = null; }
    }

    // 箭头按钮
    if (nextBtn) nextBtn.addEventListener('click', function () { next(); startAuto(); });
    if (prevBtn) prevBtn.addEventListener('click', function () { prev(); startAuto(); });

    // 指示点
    dots.forEach(function (dot, i) {
      dot.addEventListener('click', function () { goTo(i); startAuto(); });
    });

    // 触摸滑动支持（移动端）
    var startX = 0;
    var bannerEl = $('#heroBannerSlides');
    if (bannerEl) {
      bannerEl.addEventListener('touchstart', function (e) {
        startX = e.touches[0].clientX; stopAuto();
      }, { passive: true });
      bannerEl.addEventListener('touchend', function (e) {
        var diff = e.changedTouches[0].clientX - startX;
        if (Math.abs(diff) > 50) { diff > 0 ? prev() : next(); }
        startAuto();
      }, { passive: true });
    }

    // 鼠标悬停暂停
    var bannerSection = $('.hero-banner');
    if (bannerSection) {
      bannerSection.addEventListener('mouseenter', stopAuto);
      bannerSection.addEventListener('mouseleave', startAuto);
    }

    // 启动自动播放
    startAuto();
  }

  function initSearch() {
    var btn = $('#searchToggle');
    if (!btn) return;

    var modal = document.createElement('div');
    modal.className = 'search-modal';
    modal.id = 'searchModal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', LANG === 'en' ? 'Search' : '搜索');
    modal.setAttribute('hidden', 'true');
    modal.innerHTML =
      '<div class="search-panel">' +
        '<div class="search-head">' +
          '<input type="search" class="search-input" id="searchInput" placeholder="' + (LANG === 'en' ? 'Search articles...' : '搜索文章…') + '" autocomplete="off">' +
          '<button type="button" class="search-close" id="searchClose" aria-label="' + (LANG === 'en' ? 'Close' : '关闭') + '">✕</button>' +
        '</div>' +
        '<div class="search-results" id="searchResults"></div>' +
      '</div>';
    document.body.appendChild(modal);

    function open() {
      modal.hidden = false;
      document.body.classList.add('search-open');
      setTimeout(function () { var input = $('#searchInput'); if (input) input.focus(); }, 10);
      renderResults('');
    }
    function close() {
      modal.hidden = true;
      document.body.classList.remove('search-open');
      btn.focus();
    }
    btn.addEventListener('click', open);
    $('#searchClose').addEventListener('click', close);
    modal.addEventListener('click', function (e) { if (e.target === modal) close(); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !modal.hidden) { e.preventDefault(); close(); }
      if (e.key === '/' && modal.hidden && document.activeElement && !/input|textarea/i.test(document.activeElement.tagName)) { e.preventDefault(); open(); }
    });

    var input = $('#searchInput'), debounce;
    input.addEventListener('input', function () {
      clearTimeout(debounce);
      var q = input.value.trim();
      debounce = setTimeout(function () { renderResults(q); }, 150);
    });

    function renderResults(q) {
      var box = $('#searchResults');
      if (!q) {
        box.innerHTML = '<p class="search-hint">' + (LANG === 'en' ? 'Type to search titles, summaries, tags, and categories.' : '输入关键词搜索标题、摘要、标签与分类。') + '</p>';
        return;
      }
      box.innerHTML = '<p class="search-hint">' + (LANG === 'en' ? 'Searching…' : '搜索中…') + '</p>';
      loadArticles().then(function (list) {
        var ql = q.toLowerCase();
        var filtered = list.filter(function (a) {
          var en = a.en || {};
          var hay = [
            a.title, a.subtitle, a.summary, a.category, a.country, (a.tags || []).join(' '),
            en.title, en.subtitle, en.summary, en.category, en.country
          ].join(' ').toLowerCase();
          return hay.indexOf(ql) !== -1;
        });
        if (!filtered.length) {
          box.innerHTML = '<p class="search-empty">' + (LANG === 'en' ? 'No articles found.' : '未找到相关文章。') + '</p>';
          return;
        }
        box.innerHTML = filtered.map(function (a) {
          return '<a class="search-result" href="article.html?slug=' + encodeURIComponent(a.slug) + '">' +
            '<div class="search-result__cat">' + escapeHtml(categoryLabel(a)) + ' · ' + escapeHtml(af(a, 'country') || '') + '</div>' +
            '<div class="search-result__title">' + escapeHtml(af(a, 'title')) + '</div>' +
            '<div class="search-result__excerpt">' + escapeHtml(af(a, 'summary') || af(a, 'subtitle') || '') + '</div>' +
          '</a>';
        }).join('');
      });
    }
  }

  function initPWA() {
    if (!('serviceWorker' in navigator)) return;
    // 仅在安全上下文（https 或 localhost）注销，避免 file:// 直接打开时报错
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') return;
    // 清理旧 Service Worker 与全部缓存：Vercel 在大陆不稳定，旧 SW 的缓存策略
    // 导致部分用户长期滞留旧页面。新策略是放弃 SW 缓存，所有请求直接走网络。
    navigator.serviceWorker.getRegistrations().then(function (regs) {
      regs.forEach(function (r) { r.unregister(); });
    });
    if (window.caches) {
      caches.keys().then(function (keys) {
        keys.forEach(function (k) { caches.delete(k); });
      });
    }
  }

  function initLightbox() {
    // 避免重复创建
    if (document.querySelector('.lightbox')) return;
    var overlay = document.createElement('div');
    overlay.className = 'lightbox';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.innerHTML =
      '<button class="lightbox__close" aria-label="关闭">&times;</button>' +
      '<div class="lightbox__content"></div>' +
      '<div class="lightbox__caption"></div>';
    document.body.appendChild(overlay);
    var lbContent = overlay.querySelector('.lightbox__content');
    var lbCap = overlay.querySelector('.lightbox__caption');

    function open() {
      overlay.classList.add('is-open');
      document.body.style.overflow = 'hidden';
    }
    function close() {
      overlay.classList.remove('is-open');
      document.body.style.overflow = '';
      // 关闭后清空内容，避免下次打开闪现旧图/旧表
      setTimeout(function () {
        lbContent.innerHTML = '';
        lbCap.textContent = '';
        lbContent.removeAttribute('data-kind');
      }, 240);
    }

    // 放大图片：头图(.article-hero__image) / 题图(.article-figure) / 正文图(.markdown)
    function openImage(src, alt) {
      lbContent.setAttribute('data-kind', 'img');
      lbContent.innerHTML = '<img class="lightbox__img" alt="">';
      var im = lbContent.querySelector('img');
      im.src = src;
      im.alt = alt || '';
      lbCap.textContent = alt || '';
      lbCap.style.display = alt ? '' : 'none';
      open();
    }

    // 放大表格：正文中的表点开即全屏查看（可滚动、双指缩放）
    function openTable(tableEl) {
      var clone = tableEl.cloneNode(true);
      clone.removeAttribute('id');
      lbContent.setAttribute('data-kind', 'table');
      lbContent.innerHTML = '';
      lbContent.appendChild(clone);
      lbCap.style.display = 'none';
      open();
    }

    // 事件委托：图片或表格都可点击放大
    document.addEventListener('click', function (e) {
      // 表格（含表内单元格点击）
      var tbl = e.target.closest && e.target.closest('.markdown table');
      if (tbl) {
        e.preventDefault();
        openTable(tbl);
        return;
      }
      // 图片
      var img = e.target.closest && e.target.closest('img');
      if (!img) return;
      var allowed = img.closest('.markdown, .article-figure, .article-hero__image');
      if (!allowed) return;
      e.preventDefault();
      var full = img.getAttribute('data-full') || img.currentSrc || img.src;
      openImage(full, img.alt);
    });
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay || e.target.classList.contains('lightbox__close')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && overlay.classList.contains('is-open')) close();
    });
  }

  ready(function () {
    applyLang();
    initLangSwitch();
    initNavToggle();
    initSubscribe();
    initHome();
    initHeroBanner();
    initArticle();
    initLightbox();
    initTags();
    initSearch();
    initPWA();
  });
})();
