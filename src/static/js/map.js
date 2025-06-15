// FOODI 메인 JavaScript

// 전역 유틸리티 함수들
window.FOODI = {
	// API 호출 헬퍼
	async apiCall(url, options = {}) {
			try {
					const response = await fetch(url, {
							headers: {
									'Content-Type': 'application/json',
									...options.headers
							},
							...options
					});
					
					if (!response.ok) {
							throw new Error(`HTTP error! status: ${response.status}`);
					}
					
					return await response.json();
			} catch (error) {
					console.error('API 호출 오류:', error);
					throw error;
			}
	},
	
	// 알림 표시
	showAlert(message, type = 'info') {
			const alertDiv = document.createElement('div');
			alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
			alertDiv.innerHTML = `
					${message}
					<button type="button" class="btn-close" data-bs-dismiss="alert"></button>
			`;
			
			const container = document.querySelector('.container');
			if (container) {
					container.insertBefore(alertDiv, container.firstChild);
					
					// 5초 후 자동 제거
					setTimeout(() => {
							alertDiv.remove();
					}, 5000);
			}
	},
	
	// 로딩 표시
	showLoading(element) {
			const originalContent = element.innerHTML;
			element.innerHTML = `
					<div class="spinner-border spinner-border-sm me-2" role="status">
							<span class="visually-hidden">Loading...</span>
					</div>
					로딩중...
			`;
			element.disabled = true;
			
			return () => {
					element.innerHTML = originalContent;
					element.disabled = false;
			};
	},
	
	// 날짜 포맷팅
	formatDate(date) {
			return new Date(date).toLocaleDateString('ko-KR', {
					year: 'numeric',
					month: 'long',
					day: 'numeric',
					hour: '2-digit',
					minute: '2-digit'
			});
	},
	
	// 평점 별표 생성
	createStarRating(rating) {
			const stars = '★'.repeat(Math.floor(rating)) + '☆'.repeat(5 - Math.floor(rating));
			return `<span class="text-warning">${stars}</span>`;
	},
	
	// 가격 포맷팅
	formatPrice(price) {
			return new Intl.NumberFormat('ko-KR', {
					style: 'currency',
					currency: 'KRW'
			}).format(price);
	}
};

// 페이지 공통 초기화
document.addEventListener('DOMContentLoaded', function() {
	// 툴팁 초기화
	var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
	var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
			return new bootstrap.Tooltip(tooltipTriggerEl);
	});
	
	// 스무스 스크롤
	document.querySelectorAll('a[href^="#"]').forEach(anchor => {
			anchor.addEventListener('click', function (e) {
					e.preventDefault();
					const target = document.querySelector(this.getAttribute('href'));
					if (target) {
							target.scrollIntoView({
									behavior: 'smooth',
									block: 'start'
							});
					}
			});
	});
	
	// 카드 호버 효과
	document.querySelectorAll('.card').forEach(card => {
			card.addEventListener('mouseenter', function() {
					this.style.transform = 'translateY(-2px)';
			});
			
			card.addEventListener('mouseleave', function() {
					this.style.transform = 'translateY(0)';
			});
	});
});

// 에러 핸들링
window.addEventListener('error', function(e) {
	console.error('JavaScript 오류:', e.error);
});

// 서비스 워커 등록 (PWA 지원)
if ('serviceWorker' in navigator) {
	window.addEventListener('load', function() {
			navigator.serviceWorker.register('/static/sw.js')
					.then(function(registration) {
							console.log('ServiceWorker 등록 성공:', registration.scope);
					})
					.catch(function(error) {
							console.log('ServiceWorker 등록 실패:', error);
					});
	});
}