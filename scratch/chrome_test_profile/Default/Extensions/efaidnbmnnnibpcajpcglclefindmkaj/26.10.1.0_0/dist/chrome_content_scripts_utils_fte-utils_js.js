export const __webpack_esm_id__ = "chrome_content_scripts_utils_fte-utils_js";
export const __webpack_esm_ids__ = ["chrome_content_scripts_utils_fte-utils_js"];
export const __webpack_esm_modules__ = {

/***/ "./chrome/content_scripts/utils/fte-utils.js"
/*!***************************************************!*\
  !*** ./chrome/content_scripts/utils/fte-utils.js ***!
  \***************************************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   acrobatTouchPointClicked: () => (/* binding */ acrobatTouchPointClicked),
/* harmony export */   addFteCloseButtonListener: () => (/* binding */ addFteCloseButtonListener),
/* harmony export */   createFteTooltip: () => (/* binding */ createFteTooltip),
/* harmony export */   initFteStateAndConfig: () => (/* binding */ initFteStateAndConfig),
/* harmony export */   removeFteTooltip: () => (/* binding */ removeFteTooltip),
/* harmony export */   shouldShowFteTooltip: () => (/* binding */ shouldShowFteTooltip),
/* harmony export */   updateFteToolTipCoolDown: () => (/* binding */ updateFteToolTipCoolDown),
/* harmony export */   updateOneTimeFteToolTipCoolDown: () => (/* binding */ updateOneTimeFteToolTipCoolDown)
/* harmony export */ });
function _typeof(o) { "@babel/helpers - typeof"; return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (o) { return typeof o; } : function (o) { return o && "function" == typeof Symbol && o.constructor === Symbol && o !== Symbol.prototype ? "symbol" : typeof o; }, _typeof(o); }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: !0, configurable: !0, writable: !0 }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == _typeof(i) ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != _typeof(t) || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != _typeof(i)) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function _regenerator() { /*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE */ var e, t, r = "function" == typeof Symbol ? Symbol : {}, n = r.iterator || "@@iterator", o = r.toStringTag || "@@toStringTag"; function i(r, n, o, i) { var c = n && n.prototype instanceof Generator ? n : Generator, u = Object.create(c.prototype); return _regeneratorDefine2(u, "_invoke", function (r, n, o) { var i, c, u, f = 0, p = o || [], y = !1, G = { p: 0, n: 0, v: e, a: d, f: d.bind(e, 4), d: function d(t, r) { return i = t, c = 0, u = e, G.n = r, a; } }; function d(r, n) { for (c = r, u = n, t = 0; !y && f && !o && t < p.length; t++) { var o, i = p[t], d = G.p, l = i[2]; r > 3 ? (o = l === n) && (u = i[(c = i[4]) ? 5 : (c = 3, 3)], i[4] = i[5] = e) : i[0] <= d && ((o = r < 2 && d < i[1]) ? (c = 0, G.v = n, G.n = i[1]) : d < l && (o = r < 3 || i[0] > n || n > l) && (i[4] = r, i[5] = n, G.n = l, c = 0)); } if (o || r > 1) return a; throw y = !0, n; } return function (o, p, l) { if (f > 1) throw TypeError("Generator is already running"); for (y && 1 === p && d(p, l), c = p, u = l; (t = c < 2 ? e : u) || !y;) { i || (c ? c < 3 ? (c > 1 && (G.n = -1), d(c, u)) : G.n = u : G.v = u); try { if (f = 2, i) { if (c || (o = "next"), t = i[o]) { if (!(t = t.call(i, u))) throw TypeError("iterator result is not an object"); if (!t.done) return t; u = t.value, c < 2 && (c = 0); } else 1 === c && (t = i["return"]) && t.call(i), c < 2 && (u = TypeError("The iterator does not provide a '" + o + "' method"), c = 1); i = e; } else if ((t = (y = G.n < 0) ? u : r.call(n, G)) !== a) break; } catch (t) { i = e, c = 1, u = t; } finally { f = 1; } } return { value: t, done: y }; }; }(r, o, i), !0), u; } var a = {}; function Generator() {} function GeneratorFunction() {} function GeneratorFunctionPrototype() {} t = Object.getPrototypeOf; var c = [][n] ? t(t([][n]())) : (_regeneratorDefine2(t = {}, n, function () { return this; }), t), u = GeneratorFunctionPrototype.prototype = Generator.prototype = Object.create(c); function f(e) { return Object.setPrototypeOf ? Object.setPrototypeOf(e, GeneratorFunctionPrototype) : (e.__proto__ = GeneratorFunctionPrototype, _regeneratorDefine2(e, o, "GeneratorFunction")), e.prototype = Object.create(u), e; } return GeneratorFunction.prototype = GeneratorFunctionPrototype, _regeneratorDefine2(u, "constructor", GeneratorFunctionPrototype), _regeneratorDefine2(GeneratorFunctionPrototype, "constructor", GeneratorFunction), GeneratorFunction.displayName = "GeneratorFunction", _regeneratorDefine2(GeneratorFunctionPrototype, o, "GeneratorFunction"), _regeneratorDefine2(u), _regeneratorDefine2(u, o, "Generator"), _regeneratorDefine2(u, n, function () { return this; }), _regeneratorDefine2(u, "toString", function () { return "[object Generator]"; }), (_regenerator = function _regenerator() { return { w: i, m: f }; })(); }
function _regeneratorDefine2(e, r, n, t) { var i = Object.defineProperty; try { i({}, "", {}); } catch (e) { i = 0; } _regeneratorDefine2 = function _regeneratorDefine(e, r, n, t) { function o(r, n) { _regeneratorDefine2(e, r, function (e) { return this._invoke(r, n, e); }); } r ? i ? i(e, r, { value: n, enumerable: !t, configurable: !t, writable: !t }) : e[r] = n : (o("next", 0), o("throw", 1), o("return", 2)); }, _regeneratorDefine2(e, r, n, t); }
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

var FTE_TOOLTIP_CONTAINER_CLASS = "acrobat-fte-tooltip-container";
var EXTENSION_ENVIRONMENT_KEY = "env";
var createFteToolTipDivObject = function createFteToolTipDivObject(className, textContent) {
  var element = document.createElement('div');
  element.setAttribute('class', className);
  if (textContent && textContent.length > 0) {
    element.textContent = textContent;
  }
  return element;
};
var createFteTooltipObject = function createFteTooltipObject(fteTooltipStrings, tooltipContainerClass, arrowClass) {
  var _fteTooltipStrings$ti, _fteTooltipStrings$de, _fteTooltipStrings$bu;
  var fteTooltip = createFteToolTipDivObject(tooltipContainerClass, "");
  fteTooltip.setAttribute("class", tooltipContainerClass);
  fteTooltip.id = FTE_TOOLTIP_CONTAINER_CLASS;

  // Create the tooltip element
  var tooltip = createFteToolTipDivObject("acrobat-fte-tooltip", "");

  // Create the arrow element
  var arrow = createFteToolTipDivObject(arrowClass, "");
  tooltip.appendChild(arrow);

  // Create the title element
  if ((fteTooltipStrings === null || fteTooltipStrings === void 0 || (_fteTooltipStrings$ti = fteTooltipStrings.title) === null || _fteTooltipStrings$ti === void 0 ? void 0 : _fteTooltipStrings$ti.length) > 0) {
    var title = createFteToolTipDivObject("acrobat-fte-tooltip-title", fteTooltipStrings.title);
    tooltip.appendChild(title);
  }

  // Create the description element
  if ((fteTooltipStrings === null || fteTooltipStrings === void 0 || (_fteTooltipStrings$de = fteTooltipStrings.description) === null || _fteTooltipStrings$de === void 0 ? void 0 : _fteTooltipStrings$de.length) > 0) {
    var description = createFteToolTipDivObject("acrobat-fte-tooltip-description", fteTooltipStrings.description);
    tooltip.appendChild(description);
  }

  // Create the button element
  if ((fteTooltipStrings === null || fteTooltipStrings === void 0 || (_fteTooltipStrings$bu = fteTooltipStrings.button) === null || _fteTooltipStrings$bu === void 0 ? void 0 : _fteTooltipStrings$bu.length) > 0) {
    var button = document.createElement('button');
    button.setAttribute('class', 'acrobat-fte-tooltip-button');
    button.textContent = fteTooltipStrings.button;
    tooltip.appendChild(button);
  }

  // Append the tooltip to the container
  fteTooltip.appendChild(tooltip);
  return fteTooltip;
};
var createFteTooltip = function createFteTooltip(fteTooltipStrings, fteType) {
  var tooltipContainerClass = "acrobat-fte-tooltip-container-".concat(fteType, " acrobat-fte-tooltip-container");
  var arrowClass = "acrobat-fte-tooltip-arrow-".concat(fteType, " acrobat-fte-tooltip-arrow");
  var fteTooltip = createFteTooltipObject(fteTooltipStrings, tooltipContainerClass, arrowClass);
  fteTooltip.addEventListener("click", function (event) {
    event.preventDefault();
    event.stopPropagation();
  });
  return fteTooltip;
};
var getFteCustomCoolDownTime = /*#__PURE__*/function () {
  var _ref = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee() {
    var _yield$getLocalStorag, env, value;
    return _regenerator().w(function (_context) {
      while (1) switch (_context.n) {
        case 0:
          _context.n = 1;
          return getLocalStorageValue(EXTENSION_ENVIRONMENT_KEY);
        case 1:
          _yield$getLocalStorag = _context.v;
          env = _yield$getLocalStorag.env;
          if (!(env === "prod")) {
            _context.n = 2;
            break;
          }
          return _context.a(2, 0);
        case 2:
          value = new URLSearchParams(window.location.search).get('acrobatTouchPointFteDay');
          return _context.a(2, value ? parseInt(value) : 0);
      }
    }, _callee);
  }));
  return function getFteCustomCoolDownTime() {
    return _ref.apply(this, arguments);
  };
}();
var shouldShowFteTooltip = /*#__PURE__*/function () {
  var _ref2 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee2(tooltipConfig, fteState, enableFte) {
    var currentDate, fteTooltip;
    return _regenerator().w(function (_context2) {
      while (1) switch (_context2.n) {
        case 0:
          currentDate = new Date().getTime(); // If acrobat touchpoint clicked
          // or - fte is disabled
          if (!(fteState !== null && fteState !== void 0 && fteState.touchPointClicked || !enableFte)) {
            _context2.n = 1;
            break;
          }
          return _context2.a(2, false);
        case 1:
          // if fte is already visible
          fteTooltip = document.getElementsByClassName(FTE_TOOLTIP_CONTAINER_CLASS);
          if (!(fteTooltip.length > 0)) {
            _context2.n = 2;
            break;
          }
          return _context2.a(2, false);
        case 2:
          return _context2.a(2, currentDate > (fteState === null || fteState === void 0 ? void 0 : fteState.nextDate) && ((fteState === null || fteState === void 0 ? void 0 : fteState.count) < (tooltipConfig === null || tooltipConfig === void 0 ? void 0 : tooltipConfig.maxFteCount) || (tooltipConfig === null || tooltipConfig === void 0 ? void 0 : tooltipConfig.maxFteCount) === -1));
      }
    }, _callee2);
  }));
  return function shouldShowFteTooltip(_x, _x2, _x3) {
    return _ref2.apply(this, arguments);
  };
}();

// Define the applyCoolDown function as a standalone function
var applyCoolDown = function applyCoolDown(date, coolDown, isSeconds) {
  if (isSeconds) {
    date.setSeconds(date.getSeconds() + coolDown);
  } else {
    date.setDate(date.getDate() + coolDown);
  }
};

// Define a function to get the cooldown value based on the configuration
var getCoolDown = function getCoolDown(totalCount, fteCustomCoolDown, tooltipConfig) {
  var coolDown;
  var isSeconds;
  if (fteCustomCoolDown > 0) {
    coolDown = totalCount % 3 > 0 ? tooltipConfig.shortCoolDown * fteCustomCoolDown : tooltipConfig.longCoolDown * fteCustomCoolDown;
    isSeconds = true;
  } else {
    coolDown = totalCount % 3 > 0 ? tooltipConfig.shortCoolDown : tooltipConfig.longCoolDown;
    isSeconds = false;
  }
  return {
    coolDown: coolDown,
    isSeconds: isSeconds
  };
};
var updateFteToolTipCoolDown = /*#__PURE__*/function () {
  var _ref3 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee3(tooltipConfig, storageKey) {
    var result, currentDate, fteState, totalCount, fteCustomCoolDown, _getCoolDown, coolDown, isSeconds;
    return _regenerator().w(function (_context3) {
      while (1) switch (_context3.n) {
        case 0:
          _context3.n = 1;
          return getLocalStorageValue(storageKey);
        case 1:
          result = _context3.v;
          currentDate = new Date();
          fteState = (result === null || result === void 0 ? void 0 : result[storageKey]) || {
            count: 0,
            nextDate: currentDate.toISOString()
          };
          totalCount = fteState.count + 1; // Fetch custom cooldown time
          _context3.n = 2;
          return getFteCustomCoolDownTime();
        case 2:
          fteCustomCoolDown = _context3.v;
          // Get the cooldown value and whether it's in seconds or days
          _getCoolDown = getCoolDown(totalCount, fteCustomCoolDown, tooltipConfig), coolDown = _getCoolDown.coolDown, isSeconds = _getCoolDown.isSeconds; // Apply the cooldown to the current date
          applyCoolDown(currentDate, coolDown, isSeconds);

          // Update configuration and save it to local storage
          fteState.nextDate = currentDate.getTime();
          fteState.count = totalCount;
          _context3.n = 3;
          return setLocalStorageValue(storageKey, fteState);
        case 3:
          return _context3.a(2, fteState);
      }
    }, _callee3);
  }));
  return function updateFteToolTipCoolDown(_x4, _x5) {
    return _ref3.apply(this, arguments);
  };
}();

/**
 * Updates the cooldown state for a one-time FTE (First Time Experience) tooltip.
 * This function increments the count, next date of the first storage key.
 * When an additional storage key is provided, this optionally applies cooldown logic to the next date of the additional storage key.
 * This ensures the other storage key is updated to the same next date as the first one.
 * 
 * @param {string} storageKey - The primary storage key used to store and retrieve the FTE state
 * @param {Object} [tooltipConfig={}] - Configuration object for tooltip cooldown behavior
 * @param {string|null} [otherStorageKey=null] - Optional secondary storage key to synchronize cooldown state with
 * @returns {Promise<void>} A promise that resolves when the storage operations are complete
 */
var updateOneTimeFteToolTipCoolDown = /*#__PURE__*/function () {
  var _ref4 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee4(storageKey) {
    var tooltipConfig,
      otherStorageKey,
      currentDate,
      result,
      fteState,
      totalCount,
      fteCustomCoolDown,
      _getCoolDown2,
      coolDown,
      isSeconds,
      result_otherStorageKey,
      fteState_otherStorageKey,
      _args4 = arguments;
    return _regenerator().w(function (_context4) {
      while (1) switch (_context4.n) {
        case 0:
          tooltipConfig = _args4.length > 1 && _args4[1] !== undefined ? _args4[1] : {};
          otherStorageKey = _args4.length > 2 && _args4[2] !== undefined ? _args4[2] : null;
          currentDate = new Date();
          _context4.n = 1;
          return getLocalStorageValue(storageKey);
        case 1:
          result = _context4.v;
          fteState = (result === null || result === void 0 ? void 0 : result[storageKey]) || {
            count: 0,
            nextDate: currentDate
          };
          totalCount = (fteState.count || 0) + 1;
          fteState.count = totalCount;
          if (!otherStorageKey) {
            _context4.n = 4;
            break;
          }
          _context4.n = 2;
          return getFteCustomCoolDownTime();
        case 2:
          fteCustomCoolDown = _context4.v;
          _getCoolDown2 = getCoolDown(totalCount, fteCustomCoolDown, tooltipConfig), coolDown = _getCoolDown2.coolDown, isSeconds = _getCoolDown2.isSeconds;
          applyCoolDown(currentDate, coolDown, isSeconds);
          fteState.nextDate = currentDate.getTime();
          _context4.n = 3;
          return getLocalStorageValue(otherStorageKey);
        case 3:
          result_otherStorageKey = _context4.v;
          fteState_otherStorageKey = (result_otherStorageKey === null || result_otherStorageKey === void 0 ? void 0 : result_otherStorageKey[otherStorageKey]) || {
            count: 0,
            nextDate: currentDate
          };
          fteState_otherStorageKey.nextDate = currentDate.getTime();
          _context4.n = 4;
          return setLocalStorageValue(otherStorageKey, fteState_otherStorageKey);
        case 4:
          _context4.n = 5;
          return setLocalStorageValue(storageKey, fteState);
        case 5:
          return _context4.a(2);
      }
    }, _callee4);
  }));
  return function updateOneTimeFteToolTipCoolDown(_x6) {
    return _ref4.apply(this, arguments);
  };
}();
var removeFteTooltip = function removeFteTooltip() {
  var fteTooltipContainerClass = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : FTE_TOOLTIP_CONTAINER_CLASS;
  var fteTooltip = document.getElementsByClassName(fteTooltipContainerClass);
  if (fteTooltip.length > 0) {
    fteTooltip[0].remove();
  }
};
var initFteStateAndConfig = /*#__PURE__*/function () {
  var _ref5 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee5(storageKey) {
    var _yield$chrome$storage;
    var currentDate, fteState, _t, _t2, _t3, _t4;
    return _regenerator().w(function (_context5) {
      while (1) switch (_context5.n) {
        case 0:
          currentDate = new Date().getTime();
          fteState = {
            count: 0,
            nextDate: currentDate
          };
          _context5.n = 1;
          return chrome.storage.local.get(storageKey);
        case 1:
          _t3 = _yield$chrome$storage = _context5.v;
          _t2 = _t3 === null;
          if (_t2) {
            _context5.n = 2;
            break;
          }
          _t2 = _yield$chrome$storage === void 0;
        case 2:
          if (!_t2) {
            _context5.n = 3;
            break;
          }
          _t4 = void 0;
          _context5.n = 4;
          break;
        case 3:
          _t4 = _yield$chrome$storage[storageKey];
        case 4:
          _t = _t4;
          if (_t) {
            _context5.n = 5;
            break;
          }
          _t = fteState;
        case 5:
          fteState = _t;
          chrome.storage.local.set(_defineProperty({}, storageKey, fteState));
          return _context5.a(2, fteState);
      }
    }, _callee5);
  }));
  return function initFteStateAndConfig(_x7) {
    return _ref5.apply(this, arguments);
  };
}();
var acrobatTouchPointClicked = /*#__PURE__*/function () {
  var _ref6 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee6(storageKey) {
    var result, fteState;
    return _regenerator().w(function (_context6) {
      while (1) switch (_context6.n) {
        case 0:
          _context6.n = 1;
          return getLocalStorageValue(storageKey);
        case 1:
          result = _context6.v;
          fteState = (result === null || result === void 0 ? void 0 : result[storageKey]) || {};
          if (!(fteState !== null && fteState !== void 0 && fteState.touchPointClicked)) {
            removeFteTooltip(FTE_TOOLTIP_CONTAINER_CLASS);
            fteState.touchPointClicked = true;
            setLocalStorageValue(storageKey, fteState);
          }
        case 2:
          return _context6.a(2);
      }
    }, _callee6);
  }));
  return function acrobatTouchPointClicked(_x8) {
    return _ref6.apply(this, arguments);
  };
}();
var getLocalStorageValue = /*#__PURE__*/function () {
  var _ref7 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee7(storageKey) {
    return _regenerator().w(function (_context7) {
      while (1) switch (_context7.n) {
        case 0:
          _context7.n = 1;
          return chrome.storage.local.get(storageKey);
        case 1:
          return _context7.a(2, _context7.v);
      }
    }, _callee7);
  }));
  return function getLocalStorageValue(_x9) {
    return _ref7.apply(this, arguments);
  };
}();
var setLocalStorageValue = /*#__PURE__*/function () {
  var _ref8 = _asyncToGenerator(/*#__PURE__*/_regenerator().m(function _callee8(storageKey, value) {
    return _regenerator().w(function (_context8) {
      while (1) switch (_context8.n) {
        case 0:
          _context8.n = 1;
          return chrome.storage.local.set(_defineProperty({}, storageKey, value), function () {
            var _chrome$runtime;
            (_chrome$runtime = chrome.runtime) === null || _chrome$runtime === void 0 || _chrome$runtime.sendMessage({
              "main_op": storageKey,
              fteState: value
            });
          });
        case 1:
          return _context8.a(2, _context8.v);
      }
    }, _callee8);
  }));
  return function setLocalStorageValue(_x0, _x1) {
    return _ref8.apply(this, arguments);
  };
}();

/**
 * Adds click event listener to FTE tooltip close button
 * Used by PDF Tools FTE tooltip for consistent close button behavior
 * @param {HTMLElement} tooltip - The FTE tooltip element
 * @param {Object} options - Configuration options
 * @param {string} options.fteType - Type of FTE (e.g., "pdfTools")
 * @param {Function} options.onClose - Callback function to execute when close button is clicked
 * @param {Function} options.sendAnalytics - Analytics function to call
 * @param {Function} options.sendErrorLog - Error logging function
 */
var addFteCloseButtonListener = function addFteCloseButtonListener(tooltip) {
  var options = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
  var _options$fteType = options.fteType,
    fteType = _options$fteType === void 0 ? "pdfTools" : _options$fteType,
    onClose = options.onClose,
    sendErrorLog = options.sendErrorLog;
  var button = tooltip.querySelector(".acrobat-fte-tooltip-button");
  if (button) {
    button.addEventListener("click", function () {
      // Remove tooltip
      tooltip.remove();

      // Execute custom close handler
      if (onClose) {
        onClose();
      }

      // Remove click-outside listener using stored reference
      if (tooltip.clickOutsideHandler) {
        document.removeEventListener("click", tooltip.clickOutsideHandler);
      }
    });
  } else if (sendErrorLog) {
    sendErrorLog("FTE_CloseButtonNotFound_".concat(fteType), "Close button not found in tooltip");
  }
};


/***/ }

};

//# sourceMappingURL=chrome_content_scripts_utils_fte-utils_js.js.map