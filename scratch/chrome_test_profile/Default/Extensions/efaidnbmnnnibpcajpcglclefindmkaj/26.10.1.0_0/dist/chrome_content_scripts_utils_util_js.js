export const __webpack_esm_id__ = "chrome_content_scripts_utils_util_js";
export const __webpack_esm_ids__ = ["chrome_content_scripts_utils_util_js"];
export const __webpack_esm_modules__ = {

/***/ "./chrome/content_scripts/utils/util.js"
/*!**********************************************!*\
  !*** ./chrome/content_scripts/utils/util.js ***!
  \**********************************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   addAdobeCleanFontsToDocument: () => (/* binding */ addAdobeCleanFontsToDocument),
/* harmony export */   addBoldFontToDocument: () => (/* binding */ addBoldFontToDocument),
/* harmony export */   addFontToDocument: () => (/* binding */ addFontToDocument),
/* harmony export */   base64ToBytes: () => (/* binding */ base64ToBytes),
/* harmony export */   buildAcrobatPromotionSource: () => (/* binding */ buildAcrobatPromotionSource),
/* harmony export */   buildGdriveAuthHash: () => (/* binding */ buildGdriveAuthHash),
/* harmony export */   bytesToBase64: () => (/* binding */ bytesToBase64),
/* harmony export */   createAcrobatIconElement: () => (/* binding */ createAcrobatIconElement),
/* harmony export */   createDivElement: () => (/* binding */ createDivElement),
/* harmony export */   createSessionBackedUrl: () => (/* binding */ createSessionBackedUrl),
/* harmony export */   createTooltipElement: () => (/* binding */ createTooltipElement),
/* harmony export */   executeHtmlToPdfConversion: () => (/* binding */ executeHtmlToPdfConversion),
/* harmony export */   extractFileIdFromDriveUrl: () => (/* binding */ extractFileIdFromDriveUrl),
/* harmony export */   fetchDefaultViewershipConfig: () => (/* binding */ fetchDefaultViewershipConfig),
/* harmony export */   generateUUID: () => (/* binding */ generateUUID),
/* harmony export */   getAttributeValueFromList: () => (/* binding */ getAttributeValueFromList),
/* harmony export */   getClosestElementBySelectors: () => (/* binding */ getClosestElementBySelectors),
/* harmony export */   getDirectChild: () => (/* binding */ getDirectChild),
/* harmony export */   getDirectChildOf: () => (/* binding */ getDirectChildOf),
/* harmony export */   getElementFromParent: () => (/* binding */ getElementFromParent),
/* harmony export */   getElementListForSelectors: () => (/* binding */ getElementListForSelectors),
/* harmony export */   getElementsListBasedOnSelectors: () => (/* binding */ getElementsListBasedOnSelectors),
/* harmony export */   getFileDetails: () => (/* binding */ getFileDetails),
/* harmony export */   getFirstElementBasedOnSelectors: () => (/* binding */ getFirstElementBasedOnSelectors),
/* harmony export */   getFocusableWithin: () => (/* binding */ getFocusableWithin),
/* harmony export */   getParsedJSON: () => (/* binding */ getParsedJSON),
/* harmony export */   isAnalyticsSentInTheMonthOrSession: () => (/* binding */ isAnalyticsSentInTheMonthOrSession),
/* harmony export */   isTrustedOutlookAttachmentHost: () => (/* binding */ isTrustedOutlookAttachmentHost),
/* harmony export */   pdfFilenameFromText: () => (/* binding */ pdfFilenameFromText),
/* harmony export */   reserveSpaceForTouchPoint: () => (/* binding */ reserveSpaceForTouchPoint),
/* harmony export */   restoreSpaceForTouchPoint: () => (/* binding */ restoreSpaceForTouchPoint),
/* harmony export */   sendAnalytics: () => (/* binding */ sendAnalytics),
/* harmony export */   sendAnalyticsEvent: () => (/* binding */ sendAnalyticsEvent),
/* harmony export */   sendAnalyticsOnce: () => (/* binding */ sendAnalyticsOnce),
/* harmony export */   sendAnalyticsOncePerMonth: () => (/* binding */ sendAnalyticsOncePerMonth),
/* harmony export */   sendErrorLog: () => (/* binding */ sendErrorLog),
/* harmony export */   sendInfoLog: () => (/* binding */ sendInfoLog),
/* harmony export */   shouldShowImplicitDefaultViewerToast: () => (/* binding */ shouldShowImplicitDefaultViewerToast),
/* harmony export */   storeTargetElementForConversion: () => (/* binding */ storeTargetElementForConversion)
/* harmony export */ });
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _slicedToArray(r, e) { return _arrayWithHoles(r) || _iterableToArrayLimit(r, e) || _unsupportedIterableToArray(r, e) || _nonIterableRest(); }
function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }
function _iterableToArrayLimit(r, l) { var t = null == r ? null : "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (null != t) { var e, n, i, u, a = [], f = !0, o = !1; try { if (i = (t = t.call(r)).next, 0 === l) { if (Object(t) !== t) return; f = !1; } else for (; !(f = (e = i.call(t)).done) && (a.push(e.value), a.length !== l); f = !0); } catch (r) { o = !0, n = r; } finally { try { if (!f && null != t["return"] && (u = t["return"](), Object(u) !== u)) return; } finally { if (o) throw n; } } return a; } }
function _arrayWithHoles(r) { if (Array.isArray(r)) return r; }
function _createForOfIteratorHelper(r, e) { var t = "undefined" != typeof Symbol && r[Symbol.iterator] || r["@@iterator"]; if (!t) { if (Array.isArray(r) || (t = _unsupportedIterableToArray(r)) || e && r && "number" == typeof r.length) { t && (r = t); var _n = 0, F = function F() {}; return { s: F, n: function n() { return _n >= r.length ? { done: !0 } : { done: !1, value: r[_n++] }; }, e: function e(r) { throw r; }, f: F }; } throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); } var o, a = !0, u = !1; return { s: function s() { t = t.call(r); }, n: function n() { var r = t.next(); return a = r.done, r; }, e: function e(r) { u = !0, o = r; }, f: function f() { try { a || null == t["return"] || t["return"](); } finally { if (u) throw o; } } }; }
function _unsupportedIterableToArray(r, a) { if (r) { if ("string" == typeof r) return _arrayLikeToArray(r, a); var t = {}.toString.call(r).slice(8, -1); return "Object" === t && r.constructor && (t = r.constructor.name), "Map" === t || "Set" === t ? Array.from(r) : "Arguments" === t || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(t) ? _arrayLikeToArray(r, a) : void 0; } }
function _arrayLikeToArray(r, a) { (null == a || a > r.length) && (a = r.length); for (var e = 0, n = Array(a); e < a; e++) n[e] = r[e]; return n; }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _regenerator() { /*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE */ var e, t, r = "function" == typeof Symbol ? Symbol : {}, n = r.iterator || "@@iterator", o = r.toStringTag || "@@toStringTag"; function i(r, n, o, i) { var c = n && n.prototype instanceof Generator ? n : Generator, u = Object.create(c.prototype); return _regeneratorDefine2(u, "_invoke", function (r, n, o) { var i, c, u, f = 0, p = o || [], y = !1, G = { p: 0, n: 0, v: e, a: d, f: d.bind(e, 4), d: function d(t, r) { return i = t, c = 0, u = e, G.n = r, a; } }; function d(r, n) { for (c = r, u = n, t = 0; !y && f && !o && t < p.length; t++) { var o, i = p[t], d = G.p, l = i[2]; r > 3 ? (o = l === n) && (u = i[(c = i[4]) ? 5 : (c = 3, 3)], i[4] = i[5] = e) : i[0] <= d && ((o = r < 2 && d < i[1]) ? (c = 0, G.v = n, G.n = i[1]) : d < l && (o = r < 3 || i[0] > n || n > l) && (i[4] = r, i[5] = n, G.n = l, c = 0)); } if (o || r > 1) return a; throw y = !0, n; } return function (o, p, l) { if (f > 1) throw TypeError("Generator is already running"); for (y && 1 === p && d(p, l), c = p, u = l; (t = c < 2 ? e : u) || !y;) { i || (c ? c < 3 ? (c > 1 && (G.n = -1), d(c, u)) : G.n = u : G.v = u); try { if (f = 2, i) { if (c || (o = "next"), t = i[o]) { if (!(t = t.call(i, u))) throw TypeError("iterator result is not an object"); if (!t.done) return t; u = t.value, c < 2 && (c = 0); } else 1 === c && (t = i["return"]) && t.call(i), c < 2 && (u = TypeError("The iterator does not provide a '" + o + "' method"), c = 1); i = e; } else if ((t = (y = G.n < 0) ? u : r.call(n, G)) !== a) break; } catch (t) { i = e, c = 1, u = t; } finally { f = 1; } } return { value: t, done: y }; }; }(r, o, i), !0), u; } var a = {}; function Generator() {} function GeneratorFunction() {} function GeneratorFunctionPrototype() {} t = Object.getPrototypeOf; var c = [][n] ? t(t([][n]())) : (_regeneratorDefine2(t = {}, n, function () { return this; }), t), u = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(c); function f(e) { return Object.setPrototypeOf ? Object.setPrototypeOf(e, GeneratorFunctionPrototype) : (e.__proto__ = GeneratorFunctionPrototype, _regeneratorDefine2(e, o, "GeneratorFunction")), e.prototype = Object.create(u), e; } return GeneratorFunction.prototype = GeneratorFunctionPrototype, _regeneratorDefine2(u, "constructor", GeneratorFunctionPrototype), _regeneratorDefine2(GeneratorFunctionPrototype, "constructor", GeneratorFunction), GeneratorFunction.displayName = "GeneratorFunction", _regeneratorDefine2(GeneratorFunctionPrototype, o, "GeneratorFunction"), _regeneratorDefine2(u), _regeneratorDefine2(u, o, "Generator"), _regeneratorDefine2(u, n, function () { return this; }), _regeneratorDefine2(u, "toString", function () { return "[object Generator]"; }), (_regenerator = function _regenerator() { return { w: i, m: f }; })(); }
function _regeneratorDefine2(e, r, n, t) { var i = Object.defineProperty; try { i({}, "", {}); } catch (e) { i = 0; } _regeneratorDefine2 = function _regeneratorDefine(e, r, n, t) { function o(r, n) { _regeneratorDefine2(e, r, function (e) { return this._invoke(r, n, e); }); } r ? i ? i(e, r, { value: n, enumerable: !t, configurable: !t, writable: !t }) : e[r] = n : (o("next", 0), o("throw", 1), o("return", 2)); }, _regeneratorDefine2(e, r, n, t); }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function asyncGeneratorStep(n, t, e, r, o, a, c) { try { var i = n[a](c), u = i.value; } catch (n) { return void e(n); } i.done ? t(u) : Promise.resolve(u).then(r, o); }
function _asyncToGenerator(n) { return function () { var t = this, e = arguments; return new Promise(function (r, o) { var a = n.apply(t, e); function _next(n) { asyncGeneratorStep(a, r, o, _next, _throw, "next", n); } function _throw(n) { asyncGeneratorStep(a, r, o, _next, _throw, "throw", n); } _next(void 0); }); }; }
/*************************************************************************
 *
 * ADOBE CONFIDENTIAL
 * ___________________
 *
 *  Copyright 2024 Adobe Systems Incorporated
 *  All Rights Reserved.
 *
 * NOTICE:  All information contained herein is, and remains
 * the property of Adobe Systems Incorporated and its suppliers,
 * if any.  The intellectual and technical concepts contained
 * herein are proprietary to Adobe Systems Incorporated and its
 * suppliers and may be covered by U.S. and Foreign Patents,
 * patents in process, and are protected by trade secret or copyright law.
 * Dissemination of this information or reproduction of this material
 * is strictly forbidden unless prior written permission is obtained
 * from Adobe Systems Incorporated.
 **************************************************************************/

var sendAnalytics = function sendAnalytics(analytics) {
  try {
    chrome.runtime.sendMessage({
      main_op: "analytics",
      analytics: analytics
    });
  } catch (e) {
    // genuine error may come when extension context is invalidated
  }
};

// returns date in yyyyMM format
var formatDateForMonthlyAnalyticsEvent = function formatDateForMonthlyAnalyticsEvent(todayDate) {
  if (todayDate instanceof Date) {
    return "".concat(todayDate.getUTCFullYear()).concat((todayDate.getUTCMonth() + 1).toString().padStart(2, "0"));
  }
  return "";
};
var eventsSent = new Set();
var sendAnalyticsOnce = function sendAnalyticsOnce(eventString) {
  if (!(eventsSent !== null && eventsSent !== void 0 && eventsSent.has(eventString))) {
    eventsSent.add(eventString);
    sendAnalyticsEvent([eventString]);
  }
};
var analyticsEvents = new Map();
/**
 * Send analytics event once per month
 * * Checks object in session storage if flag is already sent for the month
 * * Checks local storage for cross tab event status
 * @param eventString
 * @param options
 * @returns {Promise<void>}
 */
var sendAnalyticsOncePerMonth = /*#__PURE__*/function () {
  var _ref = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee(eventString, options) {
    var _eventDetails$eventSt, todayDate, currentYearMonth, eventDetails, lastSentYearMonth, analyticsPayload, eventDetailsToSave, _t;
    return _regenerator().w(function (_context) {
      while (1) switch (_context.p = _context.n) {
        case 0:
          if (!eventString) {
            _context.n = 5;
            break;
          }
          _context.p = 1;
          if (analyticsEvents !== null && analyticsEvents !== void 0 && analyticsEvents.has(eventString)) {
            _context.n = 3;
            break;
          }
          todayDate = new Date();
          currentYearMonth = formatDateForMonthlyAnalyticsEvent(todayDate);
          analyticsEvents.set(eventString, currentYearMonth);
          _context.n = 2;
          return chrome.storage.local.get([eventString]);
        case 2:
          eventDetails = _context.v;
          lastSentYearMonth = eventDetails === null || eventDetails === void 0 || (_eventDetails$eventSt = eventDetails[eventString]) === null || _eventDetails$eventSt === void 0 ? void 0 : _eventDetails$eventSt.lastSentYearMonth; //only send analytics if it's not sent in this month
          if (!lastSentYearMonth || currentYearMonth > lastSentYearMonth) {
            analyticsPayload = options ? [[eventString, options]] : [eventString];
            sendAnalytics(analyticsPayload);
            // add to map with date
            eventDetailsToSave = {
              "lastSentYearMonth": currentYearMonth
            };
            chrome.storage.local.set(_defineProperty({}, eventString, eventDetailsToSave));
          }
        case 3:
          _context.n = 5;
          break;
        case 4:
          _context.p = 4;
          _t = _context.v;
        case 5:
          return _context.a(2);
      }
    }, _callee, null, [[1, 4]]);
  }));
  return function sendAnalyticsOncePerMonth(_x, _x2) {
    return _ref.apply(this, arguments);
  };
}();

// Gsuite default viewership related methods starts here.
var getDVStorageKey = function getDVStorageKey(surfaceId) {
  return "".concat(surfaceId, "-pdf-default-viewership");
};
var fetchDefaultViewershipConfig = /*#__PURE__*/function () {
  var _ref2 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee2(surfaceId) {
    var _yield$chrome$storage;
    var _t2, _t3, _t4, _t5;
    return _regenerator().w(function (_context2) {
      while (1) switch (_context2.n) {
        case 0:
          _context2.n = 1;
          return chrome.storage.local.get(getDVStorageKey(surfaceId));
        case 1:
          _t4 = _yield$chrome$storage = _context2.v;
          _t3 = _t4 === null;
          if (_t3) {
            _context2.n = 2;
            break;
          }
          _t3 = _yield$chrome$storage === void 0;
        case 2:
          if (!_t3) {
            _context2.n = 3;
            break;
          }
          _t5 = void 0;
          _context2.n = 4;
          break;
        case 3:
          _t5 = _yield$chrome$storage[getDVStorageKey(surfaceId)];
        case 4:
          _t2 = _t5;
          if (_t2) {
            _context2.n = 5;
            break;
          }
          _t2 = {};
        case 5:
          return _context2.a(2, _t2);
      }
    }, _callee2);
  }));
  return function fetchDefaultViewershipConfig(_x3) {
    return _ref2.apply(this, arguments);
  };
}();

/**
 * Checks if implicit default viewer toast should be shown for a given surface.
 * This should be called as early as possible to prevent FTE from showing.
 * @param {string} surfaceId - e.g. "gmail", "gdrive"
 * @param {Object} state - The state object to update with implicitToastShownInSession flag
 * @returns {Promise<boolean>} true if toast should be shown, false otherwise
 */
var shouldShowImplicitDefaultViewerToast = /*#__PURE__*/function () {
  var _ref3 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee3(surfaceId, state) {
    var key, result, shouldShowToast;
    return _regenerator().w(function (_context3) {
      while (1) switch (_context3.n) {
        case 0:
          key = "".concat(surfaceId, "-show-implicit-dv-toast");
          _context3.n = 1;
          return chrome.storage.local.get(key);
        case 1:
          result = _context3.v;
          shouldShowToast = result === null || result === void 0 ? void 0 : result[key];
          if (!(shouldShowToast === "true")) {
            _context3.n = 3;
            break;
          }
          _context3.n = 2;
          return chrome.storage.local.remove(key);
        case 2:
          // eslint-disable-next-line no-param-reassign -- state is used as out-parameter
          state.implicitToastShownInSession = true;
          return _context3.a(2, true);
        case 3:
          return _context3.a(2, false);
      }
    }, _callee3);
  }));
  return function shouldShowImplicitDefaultViewerToast(_x4, _x5) {
    return _ref3.apply(this, arguments);
  };
}();
// Gsuite default viewership related methods ends here.

/**
 * Creates a div element with the given class name.
 * @param {string} className
 * @returns {HTMLDivElement}
 */
var createDivElement = function createDivElement(className) {
  var divElement = document.createElement("div");
  divElement.className = className;
  return divElement;
};

/**
 * Create Acrobat icon element
 * @returns {HTMLImageElement}
 */
var createAcrobatIconElement = function createAcrobatIconElement(className, iconPath) {
  var acrobatImage = document.createElement("img");
  var iconUrl = chrome.runtime.getURL(iconPath);
  acrobatImage.setAttribute("src", iconUrl);
  acrobatImage.setAttribute("class", className);
  return acrobatImage;
};

/**
 * Creates a hover tooltip element with the given text and class name.
 * @param {string} className
 * @param {string} text
 * @returns {HTMLSpanElement}
 */
var createTooltipElement = function createTooltipElement(className, text) {
  var tooltip = document.createElement("span");
  tooltip.className = className;
  tooltip.textContent = text;
  return tooltip;
};
var isAnalyticsSentInTheMonthOrSession = function isAnalyticsSentInTheMonthOrSession(eventString) {
  return analyticsEvents === null || analyticsEvents === void 0 ? void 0 : analyticsEvents.has(eventString);
};
var sendErrorLog = function sendErrorLog(message, error) {
  chrome.runtime.sendMessage({
    main_op: "log-error",
    log: {
      message: message,
      error: error
    }
  });
};
var sendInfoLog = function sendInfoLog(message, data) {
  chrome.runtime.sendMessage({
    main_op: "log-info",
    log: _objectSpread({
      message: message
    }, data)
  });
};
var getParsedJSON = function getParsedJSON(input) {
  var parsedJSON;
  try {
    parsedJSON = JSON.parse(input);
  } catch (e) {}
  return parsedJSON;
};
var extractFileIdFromDriveUrl = function extractFileIdFromDriveUrl(url) {
  var fileId = "";
  if (!url) {
    return fileId;
  }
  try {
    var decodedUrl = decodeURIComponent(url);
    // Case 1: Google Drive links (either `/file/d/` or `/open?id=`)
    if (decodedUrl.startsWith("https://drive.google.com/") || decodedUrl.startsWith("https://docs.google.com/file")) {
      /* eg urls:
       * https://drive.google.com/file/d/FILE_ID/view
       * https://drive.google.com/open?id=FILE_ID
       * Enterprise: https://drive.google.com/a/<domain>/open?...&id=FILE_ID
       */
      fileId = new URL(decodedUrl).searchParams.get("id") || decodedUrl.split("/")[5];
    }
    // Case 2: Gmail URL with "q" as parameter pointing to a Google Doc
    else if (decodedUrl.startsWith("https://www.google.com/url")) {
      var parsedUrl = new URL(decodedUrl);
      var targetUrl = parsedUrl.searchParams.get('q');
      if (targetUrl) {
        var documentUrl = new URL(targetUrl);
        fileId = documentUrl.pathname.split('/')[3];
      }
    }
  } catch (e) {
    sendErrorLog("Error in GSuite", "Error in extracting file ID from URL");
  }
  return fileId;
};

/**
 * Get elements list in DOM for passed selectors.
 * @param selectors - array of selectors ["a","b"]
 * @param parentElement - parent element to search for selectors
 * @returns {*[]} - array of div elements for the selectors present in the DOM
 */
var getElementListForSelectors = function getElementListForSelectors() {
  var selectors = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [];
  var parentElement = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
  var elementList = new Set();
  var parent = parentElement || document;
  var _iterator = _createForOfIteratorHelper(selectors),
    _step;
  try {
    for (_iterator.s(); !(_step = _iterator.n()).done;) {
      var selector = _step.value;
      var elements = parent.getElementsByClassName(selector);
      if ((elements === null || elements === void 0 ? void 0 : elements.length) > 0) {
        var divList = Array.from(elements);
        divList === null || divList === void 0 || divList.forEach(function (div) {
          return elementList.add(div);
        });
      }
    }
  } catch (err) {
    _iterator.e(err);
  } finally {
    _iterator.f();
  }
  return Array.from(elementList);
};

/**
 * Get file details after parsing the file details element
 * @param {Element} fileDetailsElement - The file details element
 * @returns {Object} - The file details object
 */
var getFileDetails = function getFileDetails(fileDetailsElement) {
  try {
    var _fileDetailsElement$t;
    return JSON.parse(fileDetailsElement === null || fileDetailsElement === void 0 || (_fileDetailsElement$t = fileDetailsElement.textContent) === null || _fileDetailsElement$t === void 0 ? void 0 : _fileDetailsElement$t.replace(/\\/g, ""));
  } catch (ex) {
    return null;
  }
};

/**
 * Returns the first matching child element from the given parent element based on the provided selectors.
 *
 * @param {string[]} selectors - An array of class names or CSS selectors to match against.
 * @param {Element|null} parentElement - The parent DOM element to search within. If null, the document is used.
 * @returns {Element|null} - The first matching element if found, otherwise null.
 */
var getElementFromParent = function getElementFromParent(selectors, parentElement) {
  var childElements = getElementListForSelectors(selectors, parentElement);
  return childElements.length > 0 ? childElements[0] : null;
};

/**
 * Returns an array of elements matching any of the given selectors within the specified root element.
 *
 * @param {string[]} elementSelectors - An array of CSS selector strings used to match elements.
 * @param {Element|null} rootElement - The root DOM element within which to search.
 * @returns {Element[]|null} - An array of matching elements if found, otherwise null.
 */
var getElementsListBasedOnSelectors = function getElementsListBasedOnSelectors() {
  var elementSelectors = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [];
  var rootElement = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
  if (!rootElement || !Array.isArray(elementSelectors) || elementSelectors.length === 0) {
    return null;
  }
  var matchedElements = new Set();
  var _iterator2 = _createForOfIteratorHelper(elementSelectors),
    _step2;
  try {
    for (_iterator2.s(); !(_step2 = _iterator2.n()).done;) {
      var selector = _step2.value;
      var elements = rootElement.querySelectorAll(selector);
      elements.forEach(function (el) {
        return matchedElements.add(el);
      });
    }
  } catch (err) {
    _iterator2.e(err);
  } finally {
    _iterator2.f();
  }
  return matchedElements.size > 0 ? Array.from(matchedElements) : null;
};

/**
 * Returns the first element matching any of the given selectors within the specified root element.
 *
 * @param {string[]} elementSelectors - An array of CSS selector strings used to match elements.
 * @param {Element|null} rootElement - The root DOM element within which to search.
 * @returns {Element|null} - The first matching element if found, otherwise null.
 */
var getFirstElementBasedOnSelectors = function getFirstElementBasedOnSelectors() {
  var elementSelectors = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : [];
  var rootElement = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
  if (!rootElement || !Array.isArray(elementSelectors) || elementSelectors.length === 0) {
    return null;
  }
  var _iterator3 = _createForOfIteratorHelper(elementSelectors),
    _step3;
  try {
    for (_iterator3.s(); !(_step3 = _iterator3.n()).done;) {
      var selector = _step3.value;
      var element = rootElement.querySelector(selector);
      if (element) {
        return element; // Return the first matched element
      }
    }
  } catch (err) {
    _iterator3.e(err);
  } finally {
    _iterator3.f();
  }
  return null;
};

/**
 * Finds the direct child of `container` that is `element` itself or an ancestor of it.
 * @param {Element} container - The ancestor element to stop the walk at.
 * @param {Element} element - The element (or descendant) to walk up from.
 * @returns {Element|null} The direct child of `container` on the path to `element`, or null.
 */
var getDirectChild = function getDirectChild(container, element) {
  var _node;
  var node = element;
  while (node && node.parentElement !== container) {
    node = node.parentElement;
  }
  return ((_node = node) === null || _node === void 0 ? void 0 : _node.parentElement) === container ? node : null;
};

/**
 * Finds the closest ancestor matching any selector from the list.
 * @param {Element} element - Element to start from.
 * @param {string[]} [selectorsList=[]] - List of class names.
 * @returns {Element|null} Closest matching ancestor or null.
 */
var getClosestElementBySelectors = function getClosestElementBySelectors() {
  var element = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : null;
  var selectorsList = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : [];
  if (!element || !Array.isArray(selectorsList) || selectorsList.length === 0) {
    return null;
  }
  var _iterator4 = _createForOfIteratorHelper(selectorsList),
    _step4;
  try {
    for (_iterator4.s(); !(_step4 = _iterator4.n()).done;) {
      var selector = _step4.value;
      var containerElement = element.closest(selector);
      if (containerElement) return containerElement;
    }
  } catch (err) {
    _iterator4.e(err);
  } finally {
    _iterator4.f();
  }
  return null;
};

/**
 * Returns the value of the first attribute (from attrNames) present on the element, else null.
 * @param {Element} element - Element to read from.
 * @param {string[]} [attrNames=[]] - Candidate attribute names.
 * @returns {string|null} The first present attribute's value, or null.
 */
var getAttributeValueFromList = function getAttributeValueFromList() {
  var element = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : null;
  var attrNames = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : [];
  if (!element || !Array.isArray(attrNames)) {
    return null;
  }
  var _iterator5 = _createForOfIteratorHelper(attrNames),
    _step5;
  try {
    for (_iterator5.s(); !(_step5 = _iterator5.n()).done;) {
      var attrName = _step5.value;
      var value = element.getAttribute(attrName);
      if (value !== null) {
        return value;
      }
    }
  } catch (err) {
    _iterator5.e(err);
  } finally {
    _iterator5.f();
  }
  return null;
};

// Natively focusable elements plus anything carrying an explicit tabindex.
var FOCUSABLE_SELECTOR = "button, a, input, select, textarea, [tabindex]";

/**
 * Returns a focusable element for the given element: the element itself when it is
 * focusable, otherwise the first focusable descendant found within it.
 * @param {Element|null} element - Element to resolve a focus target from.
 * @returns {Element|null} The focusable element, or null when none is found.
 */
var getFocusableWithin = function getFocusableWithin(element) {
  var _element$matches;
  if (!element) return null;
  if ((_element$matches = element.matches) !== null && _element$matches !== void 0 && _element$matches.call(element, FOCUSABLE_SELECTOR)) return element;
  return element.querySelector(FOCUSABLE_SELECTOR);
};

/**
 * Extracts a PDF filename from text content.
 * Handles both bare "file.pdf" and descriptive labels like "file.pdf (23 KB)".
 * @param {string} text
 * @returns {string|null}
 */
var pdfFilenameFromText = function pdfFilenameFromText(text) {
  var titleText = (text || "").trim();
  if (titleText.toLowerCase().endsWith(".pdf")) return titleText;
  var match = titleText.match(/^(.+?\.pdf)\b/i);
  return match ? match[1].trim() : null;
};

/**
 * Shrinks the title element's own width by the touch point's footprint,
 * so the title can be truncated to make room instead of the button overlapping it.
 * Saves whatever inline width had set (if any) so it can be restored once the touchpoint is removed.
 * @param {Element} titleEl
 * @param {number} touchPointWidth
 * @param {string} datasetKey
 */
var reserveSpaceForTouchPoint = function reserveSpaceForTouchPoint(titleEl, touchPointWidth, datasetKey) {
  if (typeof touchPointWidth !== "number") return;
  var element = titleEl;
  var currentWidth = element.getBoundingClientRect().width;
  if (currentWidth > 0) {
    element.dataset[datasetKey] = element.style.width;
    element.style.width = "".concat(currentWidth - touchPointWidth, "px");
  }
};

/**
 * Restores the title element's width to whatever it was before reserveSpaceForTouchPoint ran.
 * @param {Element} titleEl
 * @param {string} datasetKey
 */
var restoreSpaceForTouchPoint = function restoreSpaceForTouchPoint(titleEl, datasetKey) {
  var element = titleEl;
  var originalWidth = element.dataset[datasetKey];
  if (originalWidth) {
    element.style.width = originalWidth;
  } else {
    element.style.removeProperty("width");
  }
  delete element.dataset[datasetKey];
};

/**
 * The returned string is used to pass xId and xLocation in the iframe url
 * The logic to parse and set the iframe url is written in index.js
 * */
var buildAcrobatPromotionSource = function buildAcrobatPromotionSource(surface, surfaceLocation, suffix) {
  if (surface && surfaceLocation) {
    if (suffix) {
      return "".concat(surface, "-").concat(surfaceLocation, "-").concat(suffix);
    }
    return "".concat(surface, "-").concat(surfaceLocation);
  }
  return "";
};

/**
 * Loads Adobe Clean font for content script usage
 * @param {Object} state - State object to track font loading status
 * @returns {void}
 */
var addFontToDocument = function addFontToDocument(state) {
  if (!(state !== null && state !== void 0 && state.adobeCleanFontAdded)) {
    // load and add the font (if we add the touch point and then load the font, it may re-render text and cause a page reflow)
    var fontURL = chrome.runtime.getURL("browser/css/fonts/AdobeClean-Regular.otf");
    var fontFace = new FontFace("AdobeClean-Regular", "url(".concat(fontURL, ")"));
    fontFace.load().then(function () {
      document.fonts.add(fontFace);
    });
    state.adobeCleanFontAdded = true;
  }
};

/**
 * Loads Adobe Clean Bold font for content script usage
 * @param {Object} state - State object to track font loading status
 * @returns {void}
 */
var addBoldFontToDocument = function addBoldFontToDocument(state) {
  if (!(state !== null && state !== void 0 && state.adobeCleanBoldFontAdded)) {
    var fontURL = chrome.runtime.getURL("browser/css/fonts/AdobeClean-Bold.otf");
    var fontFace = new FontFace("AdobeClean-Bold", "url(".concat(fontURL, ")"));
    fontFace.load().then(function () {
      document.fonts.add(fontFace);
    });
    state.adobeCleanBoldFontAdded = true;
  }
};

/**
 * Finds the direct child of a root element that contains the provided descendant.
 * @param {Element} element - Descendant element used to begin the search.
 * @param {Element} root - Root element whose direct child should be returned.
 * @returns {Element|null} The matching direct child, or null when none exists.
 */
var getDirectChildOf = function getDirectChildOf(element, root) {
  var node = element;
  while (node && node !== root) {
    if (node.parentElement === root) return node;
    node = node.parentElement;
  }
  return null;
};

/**
 * Loads and registers both the regular (weight 400) and bold (weight 700) AdobeClean fonts
 *
 * @param {object} state - Shared state object passed to each individual font loader.
 * @returns {void}
 */
var addAdobeCleanFontsToDocument = function addAdobeCleanFontsToDocument(state) {
  addFontToDocument(state);
  addBoldFontToDocument(state);
};
var sendAnalyticsEvent = function sendAnalyticsEvent(eventName) {
  var params = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  try {
    chrome.runtime.sendMessage({
      main_op: "analytics",
      analytics: [[eventName, params]]
    });
  } catch (e) {
    // genuine error may come when extension context is invalidated
  }
};

/**
 * Generates a unique ID (UUID v4).
 */
var generateUUID = function generateUUID() {
  return crypto.randomUUID();
};

/**
 * Registers a DOM element for section-level HTML-to-PDF conversion by
 * pushing it into the page-context store keyed by a unique section ID.
 * The store is read by the extraction pipeline in extractWebpageHTML.js.
 *
 * @param {string} targetSectionId - UUID that links this entry to the conversion request.
 * @param {Element} targetSectionElement - The DOM element whose subtree will be converted.
 * @returns {void}
 */
var storeTargetElementForConversion = function storeTargetElementForConversion(targetSectionId, targetSectionElement) {
  if (!window.acrobatTargetSectionHtmlStore) {
    window.acrobatTargetSectionHtmlStore = [];
  }
  window.acrobatTargetSectionHtmlStore.push({
    targetSectionId: targetSectionId,
    element: targetSectionElement
  });
};

/**
 * Mints an opaque SW-side session for a source URL (download/attachment link) so its query
 * params and any sensitive data (tokens, etc.) never appear in a visible viewer URL (history,
 * logs, etc.), then builds a dummy placeholder URL that encodes only the sessionId.
 *
 * @param {Object} options
 * @param {string} options.type - Session type identifier passed to the SW (e.g. "outlook-pdf").
 * @param {string} options.sourceUrl - The real URL whose origin/path/query params are stored server-side.
 * @param {string} options.dummyUrlHost - Host used to build the opaque placeholder URL.
 * @param {string} options.sessionParamKey - Query param name under which the sessionId is encoded.
 * @param {Object} [options.extraSessionData] - Additional fields (e.g. token) stored with the session.
 * @param {Object} [options.extraUrlParams] - Additional query params appended to the dummy URL.
 * @returns {Promise<string|null>} The opaque dummy URL, or null if the session could not be created.
 */
var createSessionBackedUrl = /*#__PURE__*/function () {
  var _ref5 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee4(_ref4) {
    var type, sourceUrl, dummyUrlHost, sessionParamKey, _ref4$extraSessionDat, extraSessionData, _ref4$extraUrlParams, extraUrlParams, parsedUrl, queryParams, response, sessionId, extraParamsString, _t6;
    return _regenerator().w(function (_context4) {
      while (1) switch (_context4.p = _context4.n) {
        case 0:
          type = _ref4.type, sourceUrl = _ref4.sourceUrl, dummyUrlHost = _ref4.dummyUrlHost, sessionParamKey = _ref4.sessionParamKey, _ref4$extraSessionDat = _ref4.extraSessionData, extraSessionData = _ref4$extraSessionDat === void 0 ? {} : _ref4$extraSessionDat, _ref4$extraUrlParams = _ref4.extraUrlParams, extraUrlParams = _ref4$extraUrlParams === void 0 ? {} : _ref4$extraUrlParams;
          if (sourceUrl) {
            _context4.n = 1;
            break;
          }
          return _context4.a(2, null);
        case 1:
          _context4.p = 1;
          parsedUrl = new URL(sourceUrl);
          queryParams = Object.fromEntries(parsedUrl.searchParams.entries());
          _context4.n = 2;
          return chrome.runtime.sendMessage({
            main_op: "create-session",
            type: type,
            data: _objectSpread({
              url: "".concat(parsedUrl.origin).concat(parsedUrl.pathname),
              queryParams: queryParams
            }, extraSessionData)
          });
        case 2:
          response = _context4.v;
          sessionId = response === null || response === void 0 ? void 0 : response.sessionId;
          if (sessionId) {
            _context4.n = 3;
            break;
          }
          return _context4.a(2, null);
        case 3:
          extraParamsString = Object.entries(extraUrlParams).map(function (_ref6) {
            var _ref7 = _slicedToArray(_ref6, 2),
              key = _ref7[0],
              value = _ref7[1];
            return "&".concat(key, "=").concat(encodeURIComponent(value));
          }).join("");
          return _context4.a(2, "https://".concat(dummyUrlHost, "/?").concat(sessionParamKey, "=").concat(encodeURIComponent(sessionId)).concat(extraParamsString));
        case 4:
          _context4.p = 4;
          _t6 = _context4.v;
          return _context4.a(2, null);
      }
    }, _callee4, null, [[1, 4]]);
  }));
  return function createSessionBackedUrl(_x6) {
    return _ref5.apply(this, arguments);
  };
}();

/**
 * Creates an html-to-pdf conversion session in the SW (which captures the source tab id and
 * original URL), then dispatches execute-direct-verb, analytics, and akamai-ping. The viewer
 * URL carries only the opaque session id — never the raw tabId / original page URL.
 *
 * @param {Object} options
 * @param {string} options.fileName - Filename for the converted PDF.
 * @param {string} options.source - Analytics source identifier.
 * @param {string} options.workflow - Analytics workflow identifier.
 * @param {string} [options.targetSectionId] - ID of the stored response element for response-level conversion.
 * @param {Element} [options.element] - Element to store for response-level conversion (with targetSectionId).
 * @param {number} [options.frameId] - Frame ID for iframe-based whole-page conversion.
 * @returns {void}
 */
var executeHtmlToPdfConversion = function executeHtmlToPdfConversion(_ref8) {
  var fileName = _ref8.fileName,
    source = _ref8.source,
    workflow = _ref8.workflow,
    targetSectionId = _ref8.targetSectionId,
    element = _ref8.element,
    frameId = _ref8.frameId;
  // Store the section clone (if any) in the page before the SW scrapes it.
  // Only store if element is provided — callers that pre-stored the clone must not push a dead entry.
  if (targetSectionId && element) {
    storeTargetElementForConversion(targetSectionId, element);
  }
  var originalUrl = window.location.href;
  sendAnalytics([["DCBrowserExt:DirectVerb:CTA:Clicked", {
    source: source,
    workflow: workflow
  }]]);
  chrome.runtime.sendMessage({
    main_op: "akamai-ping"
  });
  var promotionSource = buildAcrobatPromotionSource(source, workflow);

  // Mint an opaque session id in the SW that keys the source-tab context (tabId, original URL,
  // and — for scoped conversions — frameId / targetSectionId). Only htmlToPdfSessionId travels
  // in the viewer URL.
  var sessionParams = {
    main_op: "create-session",
    type: "html-to-pdf",
    data: {
      sourceTabUrl: originalUrl
    }
  };
  if (targetSectionId) {
    sessionParams.data.targetSectionId = targetSectionId;
  } else if (frameId) {
    sessionParams.data.frameId = frameId;
  }
  chrome.runtime.sendMessage(sessionParams, function (response) {
    var sessionId = response === null || response === void 0 ? void 0 : response.sessionId;
    if (!sessionId) {
      return;
    }
    var fileUrl = "https://convert-pdf-webpage/?htmlToPdfSessionId=".concat(encodeURIComponent(sessionId));
    chrome.runtime.sendMessage({
      main_op: "execute-direct-verb",
      fileUrl: fileUrl,
      fileName: fileName,
      viewerURL: chrome.runtime.getURL("viewer.html"),
      promotionSource: promotionSource,
      verb: "html-to-pdf",
      clickTimestamp: Date.now()
    });
  });
};

/**
 * Builds the #authuser=&gdriveEmail= hash fragment for the extension viewer URL.
 * authuser/gdriveEmail (gdrive surfaces only) must travel in the URL hash rather than the query
 * string — the hash never leaves the browser, unlike query params.
 * @param {string|number|null|undefined} authuser - Google multi-account index. Checked against
 *   `null`/`undefined` rather than truthiness, since index 0 (the primary account) is a valid
 *   value. Callers may pass either: an unset object property (`undefined`) or the result of
 *   `URLSearchParams.get()` on an absent param (`null`).
 * @param {string|null|undefined} gdriveEmail - Non-sensitive boolean placeholder or signed-in
 *   email, included only when truthy.
 * @returns {string} The hash fragment including the leading '#', or '' if neither value is set.
 */
var buildGdriveAuthHash = function buildGdriveAuthHash(authuser, gdriveEmail) {
  var hashParams = new URLSearchParams();
  if (authuser != null) {
    hashParams.set("authuser", authuser);
  }
  if (gdriveEmail) {
    hashParams.set("gdriveEmail", gdriveEmail);
  }
  var hash = hashParams.toString();
  return hash ? "#".concat(hash) : "";
};

// Hostname suffixes Outlook attachment downloads legitimately resolve to (consumer and enterprise
// OWA); downloadUrlBase/responseUrl are page-controlled and must be checked against this before trust.
var OUTLOOK_ATTACHMENT_HOSTNAME_SUFFIXES = ["outlook.live.net", "attachments.office.net"];

/**
 * Checks a page-controlled URL/hostname against the Outlook attachment hostname allowlist.
 * @param {string} url
 * @returns {boolean}
 */
var isTrustedOutlookAttachmentHost = function isTrustedOutlookAttachmentHost(url) {
  try {
    var hostname = new URL(url).hostname;
    return OUTLOOK_ATTACHMENT_HOSTNAME_SUFFIXES.some(function (suffix) {
      return hostname === suffix || hostname.endsWith(".".concat(suffix));
    });
  } catch (_unused) {
    return false;
  }
};

/**
 * @param {Uint8Array} bytes
 * @returns {string}
 */
var bytesToBase64 = function bytesToBase64(bytes) {
  var binary = "";
  bytes.forEach(function (_byte) {
    binary += String.fromCharCode(_byte);
  });
  return btoa(binary);
};

/**
 * @param {string} base64
 * @returns {Uint8Array}
 */
var base64ToBytes = function base64ToBytes(base64) {
  return Uint8Array.from(atob(base64), function (_char) {
    return _char.charCodeAt(0);
  });
};


/***/ }

};

//# sourceMappingURL=chrome_content_scripts_utils_util_js.js.map