package io.factorialsystems.authorizationservice.controller;

import io.factorialsystems.authorizationservice.dto.request.ForgotPasswordRequest;
import io.factorialsystems.authorizationservice.dto.request.RegisterRequest;
import io.factorialsystems.authorizationservice.dto.request.ResetPasswordRequest;
import io.factorialsystems.authorizationservice.dto.response.ApiResponse;
import io.factorialsystems.authorizationservice.dto.response.UserDto;
import io.factorialsystems.authorizationservice.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public ResponseEntity<ApiResponse<UserDto>> register(@Valid @RequestBody RegisterRequest request) {
        log.debug("Registration request for email: {}", request.getEmail());
        UserDto response = authService.register(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.of(response));
    }

    @PostMapping("/forgot-password")
    public ResponseEntity<ApiResponse<Map<String, String>>> forgotPassword(@Valid @RequestBody ForgotPasswordRequest request) {
        log.debug("Forgot password request for email: {}", request.getEmail());
        authService.forgotPassword(request);
        return ResponseEntity.ok(ApiResponse.of(Map.of("message", "If an account exists with this email, a password reset link has been sent")));
    }

    @PostMapping("/reset-password")
    public ResponseEntity<ApiResponse<Map<String, String>>> resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        log.debug("Password reset request");
        authService.resetPassword(request);
        return ResponseEntity.ok(ApiResponse.of(Map.of("message", "Password has been reset successfully")));
    }

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<UserDto>> getCurrentUser(@AuthenticationPrincipal Jwt jwt) {
        UUID userId = UUID.fromString(jwt.getSubject());
        UserDto userDto = authService.getCurrentUser(userId);
        return ResponseEntity.ok(ApiResponse.of(userDto));
    }
}
