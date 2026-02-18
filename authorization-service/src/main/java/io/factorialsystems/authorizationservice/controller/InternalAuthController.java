package io.factorialsystems.authorizationservice.controller;

import io.factorialsystems.authorizationservice.dto.response.ApiResponse;
import io.factorialsystems.authorizationservice.dto.response.OrganizationDto;
import io.factorialsystems.authorizationservice.dto.response.UserDto;
import io.factorialsystems.authorizationservice.exception.NotFoundException;
import io.factorialsystems.authorizationservice.model.Organization;
import io.factorialsystems.authorizationservice.repository.OrganizationRepository;
import io.factorialsystems.authorizationservice.service.AuthService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/internal")
@RequiredArgsConstructor
public class InternalAuthController {

    private final AuthService authService;
    private final OrganizationRepository organizationRepository;

    @GetMapping("/users/{userId}")
    public ResponseEntity<ApiResponse<UserDto>> getUserById(@PathVariable UUID userId) {
        log.debug("Internal request: get user by ID {}", userId);
        UserDto userDto = authService.getCurrentUser(userId);
        return ResponseEntity.ok(ApiResponse.of(userDto));
    }

    @GetMapping("/users/by-email")
    public ResponseEntity<ApiResponse<UserDto>> getUserByEmail(@RequestParam String email) {
        log.debug("Internal request: get user by email {}", email);
        UserDto userDto = authService.getUserByEmail(email);
        return ResponseEntity.ok(ApiResponse.of(userDto));
    }

    @GetMapping("/organizations/{orgId}")
    public ResponseEntity<ApiResponse<OrganizationDto>> getOrganizationById(@PathVariable UUID orgId) {
        log.debug("Internal request: get organization by ID {}", orgId);

        Organization org = organizationRepository.findById(orgId)
                .orElseThrow(() -> new NotFoundException("Organization not found"));

        OrganizationDto dto = OrganizationDto.builder()
                .id(org.getId())
                .name(org.getName())
                .slug(org.getSlug())
                .email(org.getEmail())
                .status(org.getStatus())
                .createdAt(org.getCreatedAt())
                .build();

        return ResponseEntity.ok(ApiResponse.of(dto));
    }
}
