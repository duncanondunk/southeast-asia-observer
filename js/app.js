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
    '经济产业': 'Economy & Industry', '国家观察': 'Country Watch', '供应链': 'Supply Chain',
    '地缘政治': 'Geopolitics', '新能源': 'New Energy', '气候变化': 'Climate Change',
    '水资源': 'Water Resources', '南海': 'South China Sea', '华侨华人': 'Overseas Chinese', '侨务': 'Diaspora Affairs', '移民': 'Migration', '历史': 'History', '全球': 'Worldwide', '华南': 'South China',
    '越南': 'Vietnam', '印度尼西亚': 'Indonesia', '新加坡': 'Singapore',
    '菲律宾': 'Philippines', '湄公河流域': 'Mekong Basin'
  };
  function tagI18n(t) { return LANG === 'en' ? (TAG_I18N[t] || t) : t; }

  // 按语言取文章字段（英文模式优先 a.en[field]）
  function af(a, field) {
    if (LANG === 'en' && a.en && a.en[field] != null) return a.en[field];
    return a[field];
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
  function splitMd(md) {
    var idx = md.search(/\n===EN===\s*\n/);
    if (idx < 0) return md; // 无英文部分，返回全文
    var zh = md.slice(0, idx);
    var en = md.slice(idx).replace(/^\s*===EN===\s*\n/, '');
    return LANG === 'en' ? en : zh;
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
        renderCarousel(list.filter(function (a) { return a.featured; }));
        renderLatest(list);
        renderRanking(list);
        renderCategorySections(list);
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
      return '' +
        '<div class="slide ' + slideClasses[i % 3] + '">' +
          '<div class="slide__overlay"></div>' +
          '<div class="slide__content">' +
            '<span class="slide__cat">' + escapeHtml(af(a, 'category')) + '</span>' +
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

  function articleCardHtml(a, coverSeed) {
    var coverClass = 'article-card__cover--' + (((coverSeed || 1) - 1) % 5 + 1);
    var share = shareLinks(a);
    return '' +
      '<article class="article-card">' +
        '<a class="article-card__cover ' + coverClass + '" href="article.html?slug=' + encodeURIComponent(a.slug) + '" aria-label="' + escapeHtml(af(a, 'title')) + '">' +
          '<span class="cover__tag">' + escapeHtml(af(a, 'country') || af(a, 'category')) + '</span>' +
        '</a>' +
        '<div class="article-card__body">' +
          '<div class="article-card__share">' +
            '<a href="' + share.x + '" target="_blank" rel="noopener" title="X">𝕏</a>' +
            '<a href="' + share.fb + '" target="_blank" rel="noopener" title="Facebook">f</a>' +
            '<a href="' + share.mail + '" title="' + (LANG === 'en' ? 'Email' : '邮件') + '">✉</a>' +
          '</div>' +
          '<div class="article-card__cat">' + escapeHtml(af(a, 'category')) + '</div>' +
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
    var groups = {};
    list.forEach(function (a) { var c = af(a, 'category'); (groups[c] = groups[c] || []).push(a); });
    var order = LANG === 'en'
      ? ['Overseas Chinese', 'Geopolitics', 'Economy & Industry', 'Climate Change', 'Society & Culture']
      : ['华侨华人', '地缘政治', '经济产业', '气候变化', '社会文化'];
    var cats = Object.keys(groups).sort(function (x, y) {
      var ix = order.indexOf(x), iy = order.indexOf(y);
      return (ix < 0 ? 99 : ix) - (iy < 0 ? 99 : iy);
    });
    // 中文标签键用于 URL（保持稳定）
    var catKey = function (cat) {
      var inv = {}; Object.keys(TAG_I18N).forEach(function (k) { inv[TAG_I18N[k]] = k; });
      return inv[cat] || cat;
    };
    var html = '';
    cats.forEach(function (cat, ci) {
      var items = groups[cat];
      var isAlt = ci % 2 === 1;
      html += '<section class="section' + (isAlt ? ' section--alt' : '') + '"><div class="container">';
      html += '<div class="section__head"><h2 class="section__title">' + escapeHtml(cat) + '</h2><a class="section__more" href="tags.html?tag=' + encodeURIComponent(catKey(cat)) + '">' + (LANG === 'en' ? 'View all →' : '查看全部 →') + '</a></div>';
      html += '<div class="cat-grid"><div class="article-list">';
      items.forEach(function (a, i) { html += articleCardHtml(a, ci * 10 + i + 1); });
      html += '</div><aside class="ranking"><h3 class="ranking__title">' + (LANG === 'en' ? 'Top in section' : '本分类热读') + ' <span>Most Read</span></h3><div>';
      items.slice(0, 5).forEach(function (a, i) {
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

        $('#articleCat').textContent = af(a, 'category');
        $('#articleTitle').textContent = af(a, 'title');
        $('#articleSub').textContent = af(a, 'subtitle') || '';
        $('#articleMeta').innerHTML =
          '<span>' + escapeHtml(authorName()) + '</span><span class="sep">|</span>' +
          '<span>' + formatDate(a.date) + '</span><span class="sep">|</span>' +
          '<span>' + readingLabel(a.readingTime || 5) + '</span><span class="sep">|</span>' +
          '<span>' + escapeHtml(af(a, 'country') || '') + '</span>';

        var tagsHtml = (a.tags || []).map(function (t) {
          return '<a class="tag" href="tags.html?tag=' + encodeURIComponent(t) + '">' + escapeHtml(tagI18n(t)) + '</a>';
        }).join('');
        $('#articleTags').innerHTML = tagsHtml;

        initArticleShare(a);

        return loadMarkdown(a).then(function (md) {
          var body = $('#articleBody');
          body.innerHTML = renderMarkdown(splitMd(md));
          $$('h2, h3', body).forEach(function (h, i) { h.id = 'sec-' + i; });
          buildToc(body);
          buildPostNav(list, idx);
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

  function shareLinks(a) {
    var url = location.origin + location.pathname.replace(/[^/]*$/, '') + 'article.html?slug=' + encodeURIComponent(a.slug);
    var text = encodeURIComponent(af(a, 'title') + ' · Southeast Asia Watch');
    var u = encodeURIComponent(url);
    return {
      x: 'https://twitter.com/intent/tweet?text=' + text + '&url=' + u,
      fb: 'https://www.facebook.com/sharer/sharer.php?u=' + u,
      mail: 'mailto:?subject=' + text + '&body=' + encodeURIComponent('Recommended: ') + u
    };
  }
  function initArticleShare(a) {
    var s = shareLinks(a);
    $('#shareX').href = s.x; $('#shareFb').href = s.fb; $('#shareMail').href = s.mail;
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

  /* ============================================================
   * 标签页
   * ============================================================ */
  function initTags() {
    if (!$('#tagCloud')) return;
    loadArticles()
      .then(function (list) {
        var counts = {};
        list.forEach(function (a) { (a.tags || []).forEach(function (t) { counts[t] = (counts[t] || 0) + 1; }); });
        var tags = Object.keys(counts).sort(function (x, y) { return counts[y] - counts[x]; });
        $('#tagCloud').innerHTML = tags.map(function (t) {
          return '<a class="tag" href="tags.html?tag=' + encodeURIComponent(t) + '">' + escapeHtml(tagI18n(t)) + '<span class="tag-count">' + counts[t] + '</span></a>';
        }).join('');
        renderFilterBar(tags, list);
        applyFilter(getQuery('tag'), list);
      })
      .catch(function (err) {
        console.error('tags load failed:', err);
        $('#gridList').innerHTML = '<div class="empty">' + (LANG === 'en' ? 'Load failed' : '加载失败') + '</div>';
      });
  }

  function renderFilterBar(tags, list) {
    var bar = $('#filterBar');
    bar.innerHTML = '<button class="tag is-active" data-tag="">' + (LANG === 'en' ? 'All' : '全部') + '</button>' +
      tags.map(function (t) {
        return '<button class="tag" data-tag="' + escapeHtml(t) + '" data-show="' + escapeHtml(tagI18n(t)) + '">' + escapeHtml(tagI18n(t)) + '</button>';
      }).join('');
    $$('.tag', bar).forEach(function (btn) {
      btn.addEventListener('click', function () {
        $$('.tag', bar).forEach(function (b) { b.classList.remove('is-active'); });
        btn.classList.add('is-active');
        applyFilter(btn.dataset.tag, list, tags);
        var newUrl = btn.dataset.tag ? 'tags.html?tag=' + encodeURIComponent(btn.dataset.tag) : 'tags.html';
        history.replaceState(null, '', newUrl);
      });
    });
  }

  function applyFilter(tag, list) {
    var box = $('#gridList');
    // tag 是中文键；筛选时按原始中文 tag 匹配
    var filtered = tag ? list.filter(function (a) { return (a.tags || []).indexOf(tag) !== -1; }) : list;
    if (!filtered.length) {
      box.innerHTML = '<div class="empty" style="grid-column:1/-1;"><div class="empty__emoji">🗂️</div>' +
        (LANG === 'en' ? 'No articles for "' + escapeHtml(tag ? tagI18n(tag) : '') + '".' : '暂无「' + escapeHtml(tag || '') + '」相关文章。') + '</div>';
      return;
    }
    box.innerHTML = filtered.map(function (a) {
      return '<article class="grid-card">' +
        '<div class="grid-card__cat">' + escapeHtml(af(a, 'category')) + ' · ' + escapeHtml(af(a, 'country') || '') + '</div>' +
        '<h3 class="grid-card__title"><a href="article.html?slug=' + encodeURIComponent(a.slug) + '">' + escapeHtml(af(a, 'title')) + '</a></h3>' +
        '<p class="grid-card__excerpt">' + escapeHtml(af(a, 'summary') || af(a, 'subtitle') || '') + '</p>' +
        '<div class="grid-card__meta"><span>' + formatDateShort(a.date) + '</span><span>' + readingLabel(a.readingTime || 5) + '</span></div>' +
      '</article>';
    }).join('');
    var bar = $('#filterBar');
    $$('.tag', bar).forEach(function (b) { b.classList.toggle('is-active', b.dataset.tag === (tag || '')); });
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
  function initPWA() {
    if (!('serviceWorker' in navigator)) return;
    // 仅在安全上下文（https 或 localhost）注册，避免 file:// 直接打开时报错
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') return;
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('./sw.js').then(function (reg) {
        console.log('[PWA] Service worker registered:', reg.scope);
      }).catch(function (err) {
        console.warn('[PWA] Service worker registration failed:', err);
      });
    });
  }

  ready(function () {
    applyLang();
    initLangSwitch();
    initNavToggle();
    initSubscribe();
    initHome();
    initArticle();
    initTags();
    initPWA();
  });
})();
