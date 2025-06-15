// static/js/main.js
	// FOODI 프로젝트 메인 JavaScript 파일 - 공통 기능과 유틸리티

	/**
	 * 메인 앱 객체 - 전역 상태와 공통 기능 관리
	 */
	window.FOODI = {
		// 앱 설정
		config: {
				apiBaseUrl: '/api',
				sessionTimeout: 30 * 60 * 1000, // 30분
				maxRetries: 3,
				retryDelay: 1000
		},
		
		// 전역 상태
		state: {
				currentUser: null,
				isLoading: false,
				chatHistory: [],
				selectedRestaurant: null
		},
		
		// 이벤트 리스너들
		listeners: new Map(),
		
		// 초기화
		init() {
				this.setupGlobalEventListeners();
				this.loadUserSession();
				this.setupErrorHandling();
				console.log('FOODI 앱이 초기화되었습니다.');
		},
		
		// 전역 이벤트 리스너 설정
		setupGlobalEventListeners() {
				// 페이지 언로드 시 세션 저장
				window.addEventListener('beforeunload', () => {
						this.saveUserSession();
				});
				
				// 온라인/오프라인 상태 감지
				window.addEventListener('online', () => {
						this.showNotification('인터넷 연결이 복구되었습니다.', 'success');
				});
				
				window.addEventListener('offline', () => {
						this.showNotification('인터넷 연결이 끊어졌습니다.', 'warning');
				});
		},
		
		// 전역 에러 핸들링
		setupErrorHandling() {
				window.addEventListener('error', (event) => {
						console.error('전역 에러:', event.error);
						this.showNotification('예상치 못한 오류가 발생했습니다.', 'error');
				});
				
				window.addEventListener('unhandledrejection', (event) => {
						console.error('처리되지 않은 Promise 거부:', event.reason);
						this.showNotification('서버 요청 중 오류가 발생했습니다.', 'error');
				});
		},
		
		// 사용자 세션 로드
		loadUserSession() {
				try {
						const sessionData = sessionStorage.getItem('foodi_session');
						if (sessionData) {
								const parsed = JSON.parse(sessionData);
								this.state.currentUser = parsed.user;
								this.state.chatHistory = parsed.chatHistory || [];
						}
				} catch (error) {
						console.warn('세션 데이터 로드 실패:', error);
				}
		},
		
		// 사용자 세션 저장
		saveUserSession() {
				try {
						const sessionData = {
								user: this.state.currentUser,
								chatHistory: this.state.chatHistory,
								timestamp: Date.now()
						};
						sessionStorage.setItem('foodi_session', JSON.stringify(sessionData));
				} catch (error) {
						console.warn('세션 데이터 저장 실패:', error);
				}
		}
};

/**
 * HTTP 요청을 위한 API 클라이언트
 */
window.APIClient = {
		// 기본 요청 옵션
		defaultOptions: {
				headers: {
						'Content-Type': 'application/json',
				},
				credentials: 'same-origin'
		},
		
		// GET 요청
		async get(url, options = {}) {
				return this.request('GET', url, null, options);
		},
		
		// POST 요청
		async post(url, data = null, options = {}) {
				return this.request('POST', url, data, options);
		},
		
		// PUT 요청
		async put(url, data = null, options = {}) {
				return this.request('PUT', url, data, options);
		},
		
		// DELETE 요청
		async delete(url, options = {}) {
				return this.request('DELETE', url, null, options);
		},
		
		// 기본 요청 메서드
		async request(method, url, data = null, options = {}) {
				const fullUrl = url.startsWith('http') ? url : `${FOODI.config.apiBaseUrl}${url}`;
				
				const requestOptions = {
						...this.defaultOptions,
						...options,
						method,
						headers: {
								...this.defaultOptions.headers,
								...options.headers
						}
				};
				
				if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
						requestOptions.body = JSON.stringify(data);
				}
				
				try {
						FOODI.state.isLoading = true;
						const response = await this.fetchWithRetry(fullUrl, requestOptions);
						
						if (!response.ok) {
								throw new Error(`HTTP ${response.status}: ${response.statusText}`);
						}
						
						const result = await response.json();
						return result;
						
				} catch (error) {
						console.error(`API 요청 실패 (${method} ${url}):`, error);
						throw error;
				} finally {
						FOODI.state.isLoading = false;
				}
		},
		
		// 재시도 로직이 포함된 fetch
		async fetchWithRetry(url, options, retries = FOODI.config.maxRetries) {
				try {
						return await fetch(url, options);
				} catch (error) {
						if (retries > 0 && this.isRetryableError(error)) {
								console.warn(`요청 실패, ${retries}번 재시도 남음:`, error.message);
								await this.delay(FOODI.config.retryDelay);
								return this.fetchWithRetry(url, options, retries - 1);
						}
						throw error;
				}
		},
		
		// 재시도 가능한 에러인지 확인
		isRetryableError(error) {
				return (
						error.name === 'NetworkError' ||
						error.message.includes('fetch') ||
						error.message.includes('network')
				);
		},
		
		// 지연 함수
		delay(ms) {
				return new Promise(resolve => setTimeout(resolve, ms));
		}
};

/**
 * 알림 시스템
 */
window.NotificationManager = {
		container: null,
		
		// 초기화
		init() {
				this.createContainer();
		},
		
		// 알림 컨테이너 생성
		createContainer() {
				if (this.container) return;
				
				this.container = document.createElement('div');
				this.container.className = 'notification-container';
				this.container.style.cssText = `
						position: fixed;
						top: 20px;
						right: 20px;
						z-index: 10000;
						pointer-events: none;
				`;
				document.body.appendChild(this.container);
		},
		
		// 알림 표시
		show(message, type = 'info', duration = 5000) {
				const notification = this.createNotification(message, type);
				this.container.appendChild(notification);
				
				// 애니메이션 트리거
				requestAnimationFrame(() => {
						notification.style.transform = 'translateX(0)';
						notification.style.opacity = '1';
				});
				
				// 자동 제거
				setTimeout(() => {
						this.remove(notification);
				}, duration);
				
				return notification;
		},
		
		// 알림 요소 생성
		createNotification(message, type) {
				const notification = document.createElement('div');
				notification.className = `notification notification-${type}`;
				notification.style.cssText = `
						background: white;
						border-left: 4px solid ${this.getTypeColor(type)};
						border-radius: 8px;
						box-shadow: 0 4px 12px rgba(0,0,0,0.1);
						padding: 16px 20px;
						margin-bottom: 12px;
						max-width: 350px;
						transform: translateX(100%);
						opacity: 0;
						transition: all 0.3s ease;
						pointer-events: auto;
						cursor: pointer;
						position: relative;
				`;
				
				const icon = this.getTypeIcon(type);
				notification.innerHTML = `
						<div style="display: flex; align-items: center; gap: 12px;">
								<i class="fas ${icon}" style="color: ${this.getTypeColor(type)};"></i>
								<span style="flex: 1; color: #333; font-weight: 500;">${message}</span>
								<i class="fas fa-times" style="color: #999; cursor: pointer; padding: 4px;"></i>
						</div>
				`;
				
				// 클릭으로 제거
				notification.addEventListener('click', (e) => {
						if (e.target.classList.contains('fa-times')) {
								this.remove(notification);
						}
				});
				
				return notification;
		},
		
		// 알림 제거
		remove(notification) {
				notification.style.transform = 'translateX(100%)';
				notification.style.opacity = '0';
				
				setTimeout(() => {
						if (notification.parentNode) {
								notification.parentNode.removeChild(notification);
						}
				}, 300);
		},
		
		// 타입별 색상
		getTypeColor(type) {
				const colors = {
						success: '#28a745',
						warning: '#ffc107',
						error: '#dc3545',
						info: '#17a2b8'
				};
				return colors[type] || colors.info;
		},
		
		// 타입별 아이콘
		getTypeIcon(type) {
				const icons = {
						success: 'fa-check-circle',
						warning: 'fa-exclamation-triangle',
						error: 'fa-times-circle',
						info: 'fa-info-circle'
				};
				return icons[type] || icons.info;
		}
};

// FOODI 객체에 알림 메서드 추가
FOODI.showNotification = function(message, type = 'info', duration = 5000) {
		return NotificationManager.show(message, type, duration);
};

/**
 * 유틸리티 함수들
 */
window.Utils = {
		// 날짜 포맷팅
		formatDate(date, format = 'YYYY-MM-DD HH:mm') {
				const d = new Date(date);
				const year = d.getFullYear();
				const month = String(d.getMonth() + 1).padStart(2, '0');
				const day = String(d.getDate()).padStart(2, '0');
				const hours = String(d.getHours()).padStart(2, '0');
				const minutes = String(d.getMinutes()).padStart(2, '0');
				
				return format
						.replace('YYYY', year)
						.replace('MM', month)
						.replace('DD', day)
						.replace('HH', hours)
						.replace('mm', minutes);
		},
		
		// 상대적 시간 표시
		getRelativeTime(date) {
				const now = new Date();
				const diff = now - new Date(date);
				const seconds = Math.floor(diff / 1000);
				const minutes = Math.floor(seconds / 60);
				const hours = Math.floor(minutes / 60);
				const days = Math.floor(hours / 24);
				
				if (days > 0) return `${days}일 전`;
				if (hours > 0) return `${hours}시간 전`;
				if (minutes > 0) return `${minutes}분 전`;
				return '방금 전';
		},
		
		// 문자열 단축
		truncateText(text, maxLength = 100) {
				if (text.length <= maxLength) return text;
				return text.substring(0, maxLength) + '...';
		},
		
		// 숫자 포맷팅
		formatNumber(number) {
				return number.toLocaleString('ko-KR');
		},
		
		// 가격 포맷팅
		formatPrice(price) {
				return `${this.formatNumber(price)}원`;
		},
		
		// URL 파라미터 파싱
		parseURLParams(url = window.location.href) {
				const params = new URLSearchParams(new URL(url).search);
				const result = {};
				for (const [key, value] of params) {
						result[key] = value;
				}
				return result;
		},
		
		// 디바운스 함수
		debounce(func, wait, immediate = false) {
				let timeout;
				return function executedFunction(...args) {
						const later = () => {
								timeout = null;
								if (!immediate) func(...args);
						};
						const callNow = immediate && !timeout;
						clearTimeout(timeout);
						timeout = setTimeout(later, wait);
						if (callNow) func(...args);
				};
		},
		
		// 스로틀 함수
		throttle(func, limit) {
				let inThrottle;
				return function(...args) {
						if (!inThrottle) {
								func.apply(this, args);
								inThrottle = true;
								setTimeout(() => inThrottle = false, limit);
						}
				};
		},
		
		// 로컬 스토리지 헬퍼 (안전한 JSON 처리)
		storage: {
				set(key, value) {
						try {
								localStorage.setItem(key, JSON.stringify(value));
								return true;
						} catch (error) {
								console.warn('localStorage 저장 실패:', error);
								return false;
						}
				},
				
				get(key, defaultValue = null) {
						try {
								const item = localStorage.getItem(key);
								return item ? JSON.parse(item) : defaultValue;
						} catch (error) {
								console.warn('localStorage 읽기 실패:', error);
								return defaultValue;
						}
				},
				
				remove(key) {
						try {
								localStorage.removeItem(key);
								return true;
						} catch (error) {
								console.warn('localStorage 삭제 실패:', error);
								return false;
						}
				}
		},
		
		// 세션 스토리지 헬퍼
		session: {
				set(key, value) {
						try {
								sessionStorage.setItem(key, JSON.stringify(value));
								return true;
						} catch (error) {
								console.warn('sessionStorage 저장 실패:', error);
								return false;
						}
				},
				
				get(key, defaultValue = null) {
						try {
								const item = sessionStorage.getItem(key);
								return item ? JSON.parse(item) : defaultValue;
						} catch (error) {
								console.warn('sessionStorage 읽기 실패:', error);
								return defaultValue;
						}
				},
				
				remove(key) {
						try {
								sessionStorage.removeItem(key);
								return true;
						} catch (error) {
								console.warn('sessionStorage 삭제 실패:', error);
								return false;
						}
				}
		}
};

/**
 * DOM 조작 헬퍼
 */
window.DOM = {
		// 요소 선택
		$(selector) {
				return document.querySelector(selector);
		},
		
		// 다중 요소 선택
		$$(selector) {
				return document.querySelectorAll(selector);
		},
		
		// 요소 생성
		create(tag, attributes = {}, content = '') {
				const element = document.createElement(tag);
				
				Object.entries(attributes).forEach(([key, value]) => {
						if (key === 'className') {
								element.className = value;
						} else if (key === 'innerHTML') {
								element.innerHTML = value;
						} else {
								element.setAttribute(key, value);
						}
				});
				
				if (content) {
						element.textContent = content;
				}
				
				return element;
		},
		
		// 클래스 토글
		toggleClass(element, className) {
				element.classList.toggle(className);
		},
		
		// 요소 표시/숨김
		show(element) {
				element.style.display = '';
		},
		
		hide(element) {
				element.style.display = 'none';
		},
		
		// 요소 활성화/비활성화
		enable(element) {
				element.disabled = false;
				element.classList.remove('disabled');
		},
		
		disable(element) {
				element.disabled = true;
				element.classList.add('disabled');
		},
		
		// 부드러운 스크롤
		scrollTo(element, offset = 0) {
				const targetPosition = element.offsetTop + offset;
				window.scrollTo({
						top: targetPosition,
						behavior: 'smooth'
				});
		},
		
		// 요소가 뷰포트에 있는지 확인
		isInViewport(element) {
				const rect = element.getBoundingClientRect();
				return (
						rect.top >= 0 &&
						rect.left >= 0 &&
						rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
						rect.right <= (window.innerWidth || document.documentElement.clientWidth)
				);
		}
};

/**
 * 폼 검증 헬퍼
 */
window.FormValidator = {
		// 이메일 검증
		isValidEmail(email) {
				const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
				return emailRegex.test(email);
		},
		
		// 전화번호 검증 (한국)
		isValidPhone(phone) {
				const phoneRegex = /^01[016789]-?\d{3,4}-?\d{4}$/;
				return phoneRegex.test(phone.replace(/\s/g, ''));
		},
		
		// 필수 필드 검증
		isRequired(value) {
				return value && value.trim().length > 0;
		},
		
		// 최소 길이 검증
		minLength(value, min) {
				return value && value.length >= min;
		},
		
		// 최대 길이 검증
		maxLength(value, max) {
				return !value || value.length <= max;
		},
		
		// 숫자 범위 검증
		isInRange(value, min, max) {
				const num = parseFloat(value);
				return !isNaN(num) && num >= min && num <= max;
		},
		
		// 폼 전체 검증
		validateForm(formElement, rules) {
				const errors = {};
				
				Object.entries(rules).forEach(([fieldName, fieldRules]) => {
						const field = formElement.querySelector(`[name="${fieldName}"]`);
						if (!field) return;
						
						const value = field.value;
						const fieldErrors = [];
						
						fieldRules.forEach(rule => {
								if (rule.type === 'required' && !this.isRequired(value)) {
										fieldErrors.push(rule.message || '필수 입력 항목입니다.');
								}
								else if (rule.type === 'email' && value && !this.isValidEmail(value)) {
										fieldErrors.push(rule.message || '올바른 이메일 형식이 아닙니다.');
								}
								else if (rule.type === 'minLength' && !this.minLength(value, rule.value)) {
										fieldErrors.push(rule.message || `최소 ${rule.value}자 이상 입력해주세요.`);
								}
								else if (rule.type === 'maxLength' && !this.maxLength(value, rule.value)) {
										fieldErrors.push(rule.message || `최대 ${rule.value}자까지 입력 가능합니다.`);
								}
						});
						
						if (fieldErrors.length > 0) {
								errors[fieldName] = fieldErrors;
						}
				});
				
				return {
						isValid: Object.keys(errors).length === 0,
						errors
				};
		}
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
		FOODI.init();
		NotificationManager.init();
});